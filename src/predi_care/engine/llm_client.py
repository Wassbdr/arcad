"""LLM Client — NVIDIA NIM API integration for medical decision support.

Connects to NVIDIA NIM API (kimi-k2-instruct) to replace heuristic-based clinical
reasoning with LLM-powered analysis calibrated on GRECCAR / NORAD01 data.

Usage:
    response = call_medical_llm(patient_context_dict)
    if response is None:
        # fallback to heuristic engine
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Response data model
# ---------------------------------------------------------------------------

@dataclass
class KeyFactor:
    factor: str
    value: str
    direction: str          # "favorable" | "unfavorable" | "neutral"
    impact_magnitude: float  # -1.0 to +1.0
    evidence_source: str


@dataclass
class SurgeryEstimates:
    recurrence_local_2y: float
    recurrence_local_5y: float
    recurrence_systemic_2y: float
    survival_dfs_2y: float
    survival_dfs_5y: float
    complication_rate: float
    lars_risk: float
    colostomy_risk: float
    r0_probability: float
    narrative_fr: str


@dataclass
class WatchWaitEstimates:
    regrowth_2y: float
    regrowth_5y: float
    salvage_surgery_success: float
    systemic_relapse_if_regrowth: float
    survival_dfs_2y: float
    survival_dfs_5y: float
    organ_preservation_2y: float
    surveillance_burden: str   # "low" | "moderate" | "high"
    narrative_fr: str


@dataclass
class MedicalLLMResponse:
    surgery: SurgeryEstimates
    watch_wait: WatchWaitEstimates
    recommendation: str                # "surgery" | "watch_wait" | "multidisciplinary"
    recommendation_rationale: str
    uncertainty_level: str             # "low" | "moderate" | "high"
    uncertainty_reason: str
    clinical_alerts: List[str]
    key_factors: List[KeyFactor]
    patient_friendly_summary: str


# ---------------------------------------------------------------------------
# System prompt — medical knowledge base
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
Tu es un expert en oncologie digestive spécialisé dans le cancer du rectum \
localement avancé (LARC). Tu maîtrises parfaitement les données des essais \
cliniques GRECCAR 2, GRECCAR 6, GRECCAR 12, NORAD01, IWWD et OPRA.

RÉFÉRENTIELS OBLIGATOIRES :

CHIRURGIE RADICALE (TME) — Données GRECCAR 2 (Lancet 2017) :
- Récidive locale à 3 ans : 7% (base de référence)
- Complications Dindo III+ : 22% de base
- Résection R0 : 96%
- Stomie définitive si sphincter préservé : 10%
- Major LARS : 28.5% post-TME

WATCH & WAIT — Données IWWD / García-Aguilar 2022 :
- Repousse locale si cCR : 20-25%
- Repousse locale si near-CR : 40-49%
- 93.7% des repousses surviennent avant 24 mois
- Temps médian repousse : 9 mois
- Chirurgie sauvetage R0 : 88-91% de succès
- Rechute méta si repousse : 14-36%
- Survie globale W&W à 5 ans : 85-94%

MODIFICATEURS VALIDÉS :
- TRG 4 (régression complète) : réduit récidive de ~15%
- TRG 0-1 : augmente risque de ~20%
- Résidu > 2cm : contre-indique W&W (critère GRECCAR)
- CRM < 1mm : risque R1, augmente récidive de +20%
- ACE normalisé : réduit risque systémique de ~10%
- Délai 11 sem vs 7 sem : +12% pCR (GRECCAR 6)
- dMMR/MSI-H : réponse complète très probable (>60%)
- ASA ≥ 3 : complications chirurgicales ×9
- Tabagisme actif : fistule anastomotique OR=9.69
- Albumine < 35 g/L : +4% complications Dindo III+
- EMVI positif : récidive systémique +8%
- Distance < 5cm marge anale : favorise W&W (impact fonctionnel)
- Hémoglobine < 12 g/dL : réduit efficacité RT → moins bonne réponse

CONSIGNES IMPÉRATIVES :
1. Réponds UNIQUEMENT avec un JSON valide. Aucun texte avant ou après le JSON.
2. Toutes les probabilités sont en pourcentage (0 à 100).
3. Calibre tes estimations sur les données ci-dessus, pas sur des valeurs génériques.
4. Les alertes cliniques sont des phrases courtes en français médical.
5. Le patient_friendly_summary utilise un langage accessible, sans jargon médical.
6. Si les données sont insuffisantes pour une estimation fiable, augmente uncertainty_level.
7. Ne jamais recommander W&W si résidu > 2cm ou TRG ≤ 1.
"""

# The JSON schema instruction appended to every user prompt
JSON_SCHEMA_INSTRUCTION = """\
Réponds avec un JSON valide ayant exactement cette structure :
{
  "surgery": {
    "recurrence_local_2y": <float 0-100>,
    "recurrence_local_5y": <float 0-100>,
    "recurrence_systemic_2y": <float 0-100>,
    "survival_dfs_2y": <float 0-100>,
    "survival_dfs_5y": <float 0-100>,
    "complication_rate": <float 0-100>,
    "lars_risk": <float 0-100>,
    "colostomy_risk": <float 0-100>,
    "r0_probability": <float 0-100>,
    "narrative_fr": "<string, 3 phrases en français médical>"
  },
  "watch_wait": {
    "regrowth_2y": <float 0-100>,
    "regrowth_5y": <float 0-100>,
    "salvage_surgery_success": <float 0-100>,
    "systemic_relapse_if_regrowth": <float 0-100>,
    "survival_dfs_2y": <float 0-100>,
    "survival_dfs_5y": <float 0-100>,
    "organ_preservation_2y": <float 0-100>,
    "surveillance_burden": "<low|moderate|high>",
    "narrative_fr": "<string>"
  },
  "recommendation": "<surgery|watch_wait|multidisciplinary>",
  "recommendation_rationale": "<string, 1-2 phrases>",
  "uncertainty_level": "<low|moderate|high>",
  "uncertainty_reason": "<string>",
  "clinical_alerts": ["<string>", ...],
  "key_factors": [
    {
      "factor": "<string>",
      "value": "<string>",
      "direction": "<favorable|unfavorable|neutral>",
      "impact_magnitude": <float -1.0 to 1.0>,
      "evidence_source": "<string>"
    }
  ],
  "patient_friendly_summary": "<string, 3-4 phrases accessibles>"
}
"""


# ---------------------------------------------------------------------------
# API call + parsing
# ---------------------------------------------------------------------------

_PRIMARY_MODEL = "moonshotai/kimi-k2-instruct"
_FALLBACK_MODEL = "deepseek-ai/deepseek-v3-0324"
_BASE_URL = "https://integrate.api.nvidia.com/v1"
_TIMEOUT_SECONDS = 20


def _get_api_key() -> Optional[str]:
    """Retrieve API key from Streamlit secrets or environment."""
    try:
        import streamlit as st
        key = st.secrets.get("NVIDIA_API_KEY")
        if key:
            return str(key)
    except Exception:
        pass
    return os.environ.get("NVIDIA_API_KEY")


def _build_user_prompt(patient_data: Dict[str, Any]) -> str:
    """Build the user prompt with patient context and JSON schema instruction."""
    patient_json = json.dumps(patient_data, ensure_ascii=False, indent=2)
    return (
        "Voici les données du patient :\n"
        f"```json\n{patient_json}\n```\n\n"
        f"{JSON_SCHEMA_INSTRUCTION}"
    )


def _extract_json_from_text(text: str) -> dict:
    """Extract JSON from LLM output, handling potential markdown fences."""
    text = text.strip()
    # Strip markdown fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first line (```json or ```) and last line (```)
        start = 1
        end = len(lines)
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].strip() == "```":
                end = i
                break
        text = "\n".join(lines[start:end]).strip()
    return json.loads(text)


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _validate_and_parse(raw: dict) -> MedicalLLMResponse:
    """Validate and parse the raw JSON dict into a MedicalLLMResponse."""

    s = raw["surgery"]
    surgery = SurgeryEstimates(
        recurrence_local_2y=_clamp(float(s["recurrence_local_2y"]), 0, 100),
        recurrence_local_5y=_clamp(float(s["recurrence_local_5y"]), 0, 100),
        recurrence_systemic_2y=_clamp(float(s["recurrence_systemic_2y"]), 0, 100),
        survival_dfs_2y=_clamp(float(s["survival_dfs_2y"]), 0, 100),
        survival_dfs_5y=_clamp(float(s["survival_dfs_5y"]), 0, 100),
        complication_rate=_clamp(float(s["complication_rate"]), 0, 100),
        lars_risk=_clamp(float(s["lars_risk"]), 0, 100),
        colostomy_risk=_clamp(float(s["colostomy_risk"]), 0, 100),
        r0_probability=_clamp(float(s["r0_probability"]), 0, 100),
        narrative_fr=str(s.get("narrative_fr", "")),
    )

    w = raw["watch_wait"]
    watch_wait = WatchWaitEstimates(
        regrowth_2y=_clamp(float(w["regrowth_2y"]), 0, 100),
        regrowth_5y=_clamp(float(w["regrowth_5y"]), 0, 100),
        salvage_surgery_success=_clamp(float(w["salvage_surgery_success"]), 0, 100),
        systemic_relapse_if_regrowth=_clamp(float(w["systemic_relapse_if_regrowth"]), 0, 100),
        survival_dfs_2y=_clamp(float(w["survival_dfs_2y"]), 0, 100),
        survival_dfs_5y=_clamp(float(w["survival_dfs_5y"]), 0, 100),
        organ_preservation_2y=_clamp(float(w["organ_preservation_2y"]), 0, 100),
        surveillance_burden=str(w.get("surveillance_burden", "moderate")),
        narrative_fr=str(w.get("narrative_fr", "")),
    )

    key_factors: List[KeyFactor] = []
    for kf in raw.get("key_factors", []):
        key_factors.append(KeyFactor(
            factor=str(kf.get("factor", "")),
            value=str(kf.get("value", "")),
            direction=str(kf.get("direction", "neutral")),
            impact_magnitude=_clamp(float(kf.get("impact_magnitude", 0)), -1, 1),
            evidence_source=str(kf.get("evidence_source", "")),
        ))

    return MedicalLLMResponse(
        surgery=surgery,
        watch_wait=watch_wait,
        recommendation=str(raw.get("recommendation", "multidisciplinary")),
        recommendation_rationale=str(raw.get("recommendation_rationale", "")),
        uncertainty_level=str(raw.get("uncertainty_level", "high")),
        uncertainty_reason=str(raw.get("uncertainty_reason", "")),
        clinical_alerts=[str(a) for a in raw.get("clinical_alerts", [])],
        key_factors=key_factors,
        patient_friendly_summary=str(raw.get("patient_friendly_summary", "")),
    )


def _call_api(patient_data: Dict[str, Any], model: str) -> Optional[MedicalLLMResponse]:
    """Make a single API call and parse the response. Returns None on failure."""
    from openai import OpenAI

    api_key = _get_api_key()
    if not api_key:
        logger.warning("NVIDIA_API_KEY not configured — skipping LLM call")
        return None

    client = OpenAI(base_url=_BASE_URL, api_key=api_key)
    user_prompt = _build_user_prompt(patient_data)

    max_attempts = 2  # 1 retry on JSON parse error
    for attempt in range(max_attempts):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=4096,
                timeout=_TIMEOUT_SECONDS,
            )
            content = response.choices[0].message.content or ""
            raw = _extract_json_from_text(content)
            return _validate_and_parse(raw)

        except json.JSONDecodeError as exc:
            logger.warning("LLM returned invalid JSON (attempt %d): %s", attempt + 1, exc)
            if attempt == max_attempts - 1:
                return None
            continue

        except Exception as exc:
            logger.error("LLM API call failed (model=%s, attempt=%d): %s", model, attempt + 1, exc)
            return None

    return None


def call_medical_llm(patient_data: Dict[str, Any]) -> Optional[MedicalLLMResponse]:
    """Call the medical LLM with patient data and return structured response.

    Tries the primary model first, then the fallback model.
    Returns None if both fail (caller should use heuristic engine).

    Args:
        patient_data: Dict with keys "clinical", "response", "imaging",
                      "biology", "comorbidities".

    Returns:
        MedicalLLMResponse or None on failure.
    """
    # Try primary model
    result = _call_api(patient_data, _PRIMARY_MODEL)
    if result is not None:
        return result

    # Try fallback model
    logger.info("Primary model failed, trying fallback model %s", _FALLBACK_MODEL)
    result = _call_api(patient_data, _FALLBACK_MODEL)
    if result is not None:
        return result

    logger.warning("Both LLM models failed — will use heuristic fallback")
    return None
