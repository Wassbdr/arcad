"""Hybrid LLM client for clinical decision support.

Priority chain:
1) OpenAI models (primary)
2) Alternate LLM endpoint/models (fallback)
3) Heuristic-only mode (no LLM answer)
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional
import tomllib
import urllib.error
import urllib.request

from predi_care.engine.v4_types import RuntimeMode

logger = logging.getLogger(__name__)


class SafeFilter(logging.Filter):
    """Mask configured API keys in logs."""

    def filter(self, record: logging.LogRecord) -> bool:
        message = str(record.getMessage())
        secrets_to_mask = [
            os.environ.get("OPENAI_API_KEY", ""),
            os.environ.get("ALT_LLM_API_KEY", ""),
            os.environ.get("NVIDIA_API_KEY", ""),
        ]
        for secret in secrets_to_mask:
            if secret:
                message = message.replace(secret, "***")
        record.msg = message
        record.args = ()
        return True


if not any(isinstance(item, SafeFilter) for item in logger.filters):
    logger.addFilter(SafeFilter())


@dataclass
class KeyFactor:
    factor: str
    value: str
    direction: str
    impact_magnitude: float
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
    narrative_fr: str = ""


@dataclass
class WatchWaitEstimates:
    regrowth_2y: float
    regrowth_5y: float
    salvage_surgery_success: float
    systemic_relapse_if_regrowth: float
    survival_dfs_2y: float
    survival_dfs_5y: float
    organ_preservation_2y: float
    surveillance_burden: str
    narrative_fr: str = ""


@dataclass
class MedicalLLMResponse:
    surgery: SurgeryEstimates
    watch_wait: WatchWaitEstimates
    recommendation: str
    recommendation_rationale: str
    uncertainty_level: str
    uncertainty_reason: str
    clinical_alerts: list[str]
    key_factors: list[KeyFactor]
    patient_friendly_summary: str


@dataclass
class LLMRuntimeResult:
    mode_runtime: RuntimeMode
    model_used: str
    response: MedicalLLMResponse | None
    errors: list[str] = field(default_factory=list)


@dataclass
class _CircuitState:
    failures: int = 0
    opened_at: float | None = None


SYSTEM_PROMPT = """
You are an expert rectal cancer clinical decision assistant.
Return only strict JSON with bounded probabilities in [0,100].
Never return watch_wait when residual_size_cm > 2 or trg > 2.
Do not include markdown in the answer.
""".strip()

JSON_SCHEMA_INSTRUCTION = """
Return this JSON schema exactly:
{
  "surgery": {
    "recurrence_local_2y": <float>,
    "recurrence_local_5y": <float>,
    "recurrence_systemic_2y": <float>,
    "survival_dfs_2y": <float>,
    "survival_dfs_5y": <float>,
    "complication_rate": <float>,
    "lars_risk": <float>,
    "colostomy_risk": <float>,
    "r0_probability": <float>,
    "narrative_fr": "<string>"
  },
  "watch_wait": {
    "regrowth_2y": <float>,
    "regrowth_5y": <float>,
    "salvage_surgery_success": <float>,
    "systemic_relapse_if_regrowth": <float>,
    "survival_dfs_2y": <float>,
    "survival_dfs_5y": <float>,
    "organ_preservation_2y": <float>,
    "surveillance_burden": "<low|moderate|high>",
    "narrative_fr": "<string>"
  },
  "recommendation": "<surgery|watch_wait|multidisciplinary>",
  "recommendation_rationale": "<string>",
  "uncertainty_level": "<low|moderate|high>",
  "uncertainty_reason": "<string>",
  "clinical_alerts": ["<string>"],
  "key_factors": [
    {
      "factor": "<string>",
      "value": "<string>",
      "direction": "<favorable|unfavorable|neutral>",
      "impact_magnitude": <float>,
      "evidence_source": "<string>"
    }
  ],
  "patient_friendly_summary": "<string>"
}
""".strip()


def _split_models(raw: str, default: list[str]) -> list[str]:
    models = [item.strip() for item in raw.split(",") if item.strip()]
    return models or default


_OPENAI_MODELS = _split_models(
    os.environ.get("OPENAI_PRIMARY_MODELS", "gpt-4o,o3-mini"),
    ["gpt-4o", "o3-mini"],
)
_ALT_MODELS = _split_models(
    os.environ.get(
        "ALT_FALLBACK_MODELS",
        "moonshotai/kimi-k2-instruct,deepseek-ai/deepseek-v3.1,glm-4.7,mistral-large-3,qwen3-coder",
    ),
    [
        "moonshotai/kimi-k2-instruct",
        "deepseek-ai/deepseek-v3.1",
        "glm-4.7",
        "mistral-large-3",
        "qwen3-coder",
    ],
)

_OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
_ALT_BASE_URL = os.environ.get("ALT_LLM_BASE_URL", "https://integrate.api.nvidia.com/v1")
_TIMEOUT_SECONDS = float(os.environ.get("LLM_TIMEOUT_SECONDS", "20"))
_MAX_RETRIES = max(1, int(os.environ.get("LLM_MAX_RETRIES", "2")))
_CIRCUIT_FAILURES = max(1, int(os.environ.get("LLM_CIRCUIT_FAILURES", "3")))
_CIRCUIT_RESET_SECONDS = max(10, int(os.environ.get("LLM_CIRCUIT_RESET_SECONDS", "90")))
_CACHE_TTL_SECONDS = max(30, int(os.environ.get("LLM_CACHE_TTL_SECONDS", "300")))
_CACHE_MAX_ITEMS = max(32, int(os.environ.get("LLM_CACHE_MAX_ITEMS", "256")))

_cache_lock = threading.Lock()
_cache: dict[str, tuple[float, LLMRuntimeResult]] = {}
_circuits = {
    "openai": _CircuitState(),
    "alt_llm": _CircuitState(),
}
_local_secret_cache: dict[str, str] | None = None
_local_secret_fingerprint: tuple[tuple[str, float], ...] | None = None


def _secret_candidates() -> list[Path]:
    return [
        Path.cwd() / ".streamlit" / "secrets.toml",
        Path.cwd() / ".streamlit" / ".secrets.toml",
        Path.cwd() / ".streamlit" / ".secret.toml",
    ]


def _secret_fingerprint() -> tuple[tuple[str, float], ...]:
    entries: list[tuple[str, float]] = []
    for candidate in _secret_candidates():
        if not candidate.exists():
            continue
        try:
            entries.append((str(candidate), float(candidate.stat().st_mtime)))
        except OSError:
            continue
    return tuple(entries)


def _get_streamlit_secret(name: str) -> Optional[str]:
    try:
        import streamlit as st

        value = st.secrets.get(name)
        if value:
            return str(value)
    except Exception:
        pass

    global _local_secret_cache, _local_secret_fingerprint
    current_fingerprint = _secret_fingerprint()
    if _local_secret_cache is None or _local_secret_fingerprint != current_fingerprint:
        _local_secret_cache = {}
        _local_secret_fingerprint = current_fingerprint
        for candidate in _secret_candidates():
            if not candidate.exists():
                continue
            try:
                with candidate.open("rb") as handle:
                    parsed = tomllib.load(handle)
                for key, raw_value in parsed.items():
                    _local_secret_cache[str(key)] = str(raw_value)
            except Exception:
                continue
    if _local_secret_cache is not None and name in _local_secret_cache:
        return _local_secret_cache[name]
    return None


def _get_openai_api_key() -> Optional[str]:
    return _get_streamlit_secret("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")


def _get_alt_api_key() -> Optional[str]:
    return (
        _get_streamlit_secret("ALT_LLM_API_KEY")
        or os.environ.get("ALT_LLM_API_KEY")
        or _get_streamlit_secret("NVIDIA_API_KEY")
        or os.environ.get("NVIDIA_API_KEY")
    )


def _get_api_key() -> Optional[str]:
    """Backward-compatible key resolver used by legacy tests."""
    return _get_openai_api_key() or _get_alt_api_key()


def _build_user_prompt(patient_data: dict[str, Any]) -> str:
    payload = json.dumps(patient_data, ensure_ascii=False, sort_keys=True)
    return f"Patient context: {payload}\n\n{JSON_SCHEMA_INSTRUCTION}"


def _extract_json_from_text(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if len(lines) >= 3:
            cleaned = "\n".join(lines[1:-1]).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end >= start:
        cleaned = cleaned[start : end + 1]
    return json.loads(cleaned)


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _validate_and_parse(raw: dict[str, Any]) -> MedicalLLMResponse:
    surgery_raw = raw.get("surgery", {})
    watch_wait_raw = raw.get("watch_wait", {})

    surgery = SurgeryEstimates(
        recurrence_local_2y=_clamp(float(surgery_raw.get("recurrence_local_2y", 0.0)), 0.0, 100.0),
        recurrence_local_5y=_clamp(float(surgery_raw.get("recurrence_local_5y", 0.0)), 0.0, 100.0),
        recurrence_systemic_2y=_clamp(float(surgery_raw.get("recurrence_systemic_2y", 0.0)), 0.0, 100.0),
        survival_dfs_2y=_clamp(float(surgery_raw.get("survival_dfs_2y", 0.0)), 0.0, 100.0),
        survival_dfs_5y=_clamp(float(surgery_raw.get("survival_dfs_5y", 0.0)), 0.0, 100.0),
        complication_rate=_clamp(float(surgery_raw.get("complication_rate", 0.0)), 0.0, 100.0),
        lars_risk=_clamp(float(surgery_raw.get("lars_risk", 0.0)), 0.0, 100.0),
        colostomy_risk=_clamp(float(surgery_raw.get("colostomy_risk", 0.0)), 0.0, 100.0),
        r0_probability=_clamp(float(surgery_raw.get("r0_probability", 0.0)), 0.0, 100.0),
        narrative_fr=str(surgery_raw.get("narrative_fr", "")),
    )

    watch_wait = WatchWaitEstimates(
        regrowth_2y=_clamp(float(watch_wait_raw.get("regrowth_2y", 0.0)), 0.0, 100.0),
        regrowth_5y=_clamp(float(watch_wait_raw.get("regrowth_5y", 0.0)), 0.0, 100.0),
        salvage_surgery_success=_clamp(
            float(watch_wait_raw.get("salvage_surgery_success", 0.0)), 0.0, 100.0
        ),
        systemic_relapse_if_regrowth=_clamp(
            float(watch_wait_raw.get("systemic_relapse_if_regrowth", 0.0)), 0.0, 100.0
        ),
        survival_dfs_2y=_clamp(float(watch_wait_raw.get("survival_dfs_2y", 0.0)), 0.0, 100.0),
        survival_dfs_5y=_clamp(float(watch_wait_raw.get("survival_dfs_5y", 0.0)), 0.0, 100.0),
        organ_preservation_2y=_clamp(float(watch_wait_raw.get("organ_preservation_2y", 0.0)), 0.0, 100.0),
        surveillance_burden=str(watch_wait_raw.get("surveillance_burden", "moderate")),
        narrative_fr=str(watch_wait_raw.get("narrative_fr", "")),
    )

    factors: list[KeyFactor] = []
    for factor_raw in raw.get("key_factors", []):
        factors.append(
            KeyFactor(
                factor=str(factor_raw.get("factor", "")),
                value=str(factor_raw.get("value", "")),
                direction=str(factor_raw.get("direction", "neutral")),
                impact_magnitude=_clamp(float(factor_raw.get("impact_magnitude", 0.0)), -1.0, 1.0),
                evidence_source=str(factor_raw.get("evidence_source", "")),
            )
        )

    recommendation = str(raw.get("recommendation", "multidisciplinary"))
    if recommendation not in {"surgery", "watch_wait", "multidisciplinary"}:
        recommendation = "multidisciplinary"

    uncertainty = str(raw.get("uncertainty_level", "high")).lower()
    if uncertainty not in {"low", "moderate", "high"}:
        uncertainty = "high"

    return MedicalLLMResponse(
        surgery=surgery,
        watch_wait=watch_wait,
        recommendation=recommendation,
        recommendation_rationale=str(raw.get("recommendation_rationale", "")),
        uncertainty_level=uncertainty,
        uncertainty_reason=str(raw.get("uncertainty_reason", "")),
        clinical_alerts=[str(item) for item in raw.get("clinical_alerts", [])],
        key_factors=factors,
        patient_friendly_summary=str(raw.get("patient_friendly_summary", "")),
    )


def _context_hash(patient_data: dict[str, Any]) -> str:
    blob = json.dumps(patient_data, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _cache_get(key: str) -> Optional[LLMRuntimeResult]:
    with _cache_lock:
        item = _cache.get(key)
        if item is None:
            return None
        ts, result = item
        if (time.time() - ts) > _CACHE_TTL_SECONDS:
            _cache.pop(key, None)
            return None
        return result


def _cache_put(key: str, value: LLMRuntimeResult) -> None:
    with _cache_lock:
        if len(_cache) >= _CACHE_MAX_ITEMS:
            oldest_key = min(_cache.keys(), key=lambda existing: _cache[existing][0])
            _cache.pop(oldest_key, None)
        _cache[key] = (time.time(), value)


def _circuit_open(provider: str) -> bool:
    state = _circuits[provider]
    if state.opened_at is None:
        return False
    if (time.time() - state.opened_at) > _CIRCUIT_RESET_SECONDS:
        state.failures = 0
        state.opened_at = None
        return False
    return True


def _record_success(provider: str) -> None:
    state = _circuits[provider]
    state.failures = 0
    state.opened_at = None


def _record_failure(provider: str) -> None:
    state = _circuits[provider]
    state.failures += 1
    if state.failures >= _CIRCUIT_FAILURES:
        state.opened_at = time.time()


def _call_model(
    *,
    api_key: str,
    base_url: str,
    model: str,
    patient_data: dict[str, Any],
) -> MedicalLLMResponse:
    prompt = _build_user_prompt(patient_data)
    endpoint = base_url.rstrip("/") + "/chat/completions"

    last_error: Exception | None = None
    for _ in range(_MAX_RETRIES):
        try:
            body = {
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
                "max_tokens": 1400,
            }
            req = urllib.request.Request(
                endpoint,
                data=json.dumps(body).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=_TIMEOUT_SECONDS) as response:
                payload = json.loads(response.read().decode("utf-8"))
            content = (
                payload.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "{}")
            )
            return _validate_and_parse(_extract_json_from_text(content))
        except (
            json.JSONDecodeError,
            TimeoutError,
            ConnectionError,
            ValueError,
            RuntimeError,
            urllib.error.HTTPError,
            urllib.error.URLError,
        ) as exc:
            last_error = exc
            continue
        except Exception as exc:  # pragma: no cover - provider-specific runtime errors
            last_error = exc
            continue

    raise RuntimeError(f"Model call failed for {model}: {type(last_error).__name__ if last_error else 'unknown'}")


def call_medical_llm_with_runtime(patient_data: dict[str, Any]) -> LLMRuntimeResult:
    if os.environ.get("LLM_FORCE_HEURISTIC", "0") == "1":
        return LLMRuntimeResult(mode_runtime="heuristic", model_used="heuristic", response=None, errors=["forced"])

    key = _context_hash(patient_data)
    cached = _cache_get(key)
    if cached is not None and cached.mode_runtime != "heuristic":
        return cached

    errors: list[str] = []

    openai_key = _get_openai_api_key()
    if openai_key and not _circuit_open("openai"):
        for model in _OPENAI_MODELS:
            try:
                response = _call_model(
                    api_key=openai_key,
                    base_url=_OPENAI_BASE_URL,
                    model=model,
                    patient_data=patient_data,
                )
                _record_success("openai")
                result = LLMRuntimeResult(
                    mode_runtime="openai",
                    model_used=model,
                    response=response,
                    errors=errors,
                )
                _cache_put(key, result)
                return result
            except Exception as exc:
                _record_failure("openai")
                errors.append(f"openai:{model}:{type(exc).__name__}")
    else:
        errors.append("openai:unavailable")

    alt_key = _get_alt_api_key()
    if alt_key and not _circuit_open("alt_llm"):
        for model in _ALT_MODELS:
            try:
                response = _call_model(
                    api_key=alt_key,
                    base_url=_ALT_BASE_URL,
                    model=model,
                    patient_data=patient_data,
                )
                _record_success("alt_llm")
                result = LLMRuntimeResult(
                    mode_runtime="alt_llm",
                    model_used=model,
                    response=response,
                    errors=errors,
                )
                _cache_put(key, result)
                return result
            except Exception as exc:
                _record_failure("alt_llm")
                errors.append(f"alt_llm:{model}:{type(exc).__name__}")
    else:
        errors.append("alt_llm:unavailable")

    result = LLMRuntimeResult(
        mode_runtime="heuristic",
        model_used="heuristic",
        response=None,
        errors=errors,
    )
    return result


def call_medical_llm(patient_data: dict[str, Any]) -> Optional[MedicalLLMResponse]:
    """Backward-compatible facade used by v2 engine/tests."""
    if _get_api_key() is None:
        return None
    return call_medical_llm_with_runtime(patient_data).response
