"""Adaptateur v4 -> contrats v2 pour conserver l'UX historique."""

from __future__ import annotations

from typing import Any

from predi_care.engine.brain_engine import BrainEngineV4
from predi_care.engine.brain_engine_v2 import DecisionResult
from predi_care.engine.crf_mapper import map_patient_input_to_crf
from predi_care.engine.crf_simulator import ClinicalRationale, ScenarioOutcome, SurvivalCurve
from predi_care.engine.llm_client import (
    KeyFactor,
    MedicalLLMResponse,
    SurgeryEstimates,
    WatchWaitEstimates,
)
from predi_care.engine.patient_types import PatientInput
from predi_care.engine.v4_types import ComplicationRisk, EngineResultV4, ScenarioResultV4


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _fr(message: str) -> str:
    replacements = {
        "Surgery has the strongest consensus signal across oncologic control and safety.": (
            "La chirurgie présente le meilleur consensus en contrôle oncologique et en sécurité."
        ),
        "Watch-and-wait has the strongest consensus signal across response and quality of life.": (
            "La stratégie Watch and Wait présente le meilleur consensus sur la réponse et la qualité de vie."
        ),
        "Agent disagreement is high; multidisciplinary arbitration is recommended.": (
            "Le désaccord inter-agents est élevé; un arbitrage pluridisciplinaire est recommandé."
        ),
        "Hard protocol constraints are triggered and require multidisciplinary review.": (
            "Des contraintes protocolaires strictes sont activées et imposent une revue pluridisciplinaire."
        ),
        "If residual lesion decreased by at least": "Si la lésion résiduelle diminuait d'au moins",
        "watch-and-wait would become eligible.": "la surveillance active deviendrait éligible.",
        "If TRG improved to 2 or less, watch-and-wait eligibility would increase.": (
            "Si le TRG s'améliorait à 2 ou moins, l'éligibilité à la surveillance active augmenterait."
        ),
        "If CEA/ACE current value dropped by 10% to": "Si la valeur actuelle de l'ACE diminuait de 10% jusqu'à",
        "watch-and-wait score would improve.": "le score de surveillance active s'améliorerait.",
        "If CRM margin improved by 1 mm, surgery confidence would increase.": (
            "Si la marge CRM s'améliorait de 1 mm, la confiance pour la chirurgie augmenterait."
        ),
        "Residual lesion above 2 cm blocks watch-and-wait recommendation.": (
            "Une lésion résiduelle au-dessus de 2 cm contre-indique la surveillance active."
        ),
        "TRG above 2 blocks watch-and-wait recommendation.": (
            "Un TRG supérieur à 2 contre-indique la surveillance active."
        ),
        "cM1 requires multidisciplinary escalation.": (
            "Le stade cM1 impose une escalade pluridisciplinaire."
        ),
        "ECOG 4 contraindicates surgery and requires multidisciplinary escalation.": (
            "Un ECOG 4 contre-indique la chirurgie et impose une escalade pluridisciplinaire."
        ),
        "Des contraintes protocolaires strictes sont activees et imposent une revue pluridisciplinaire.": (
            "Des contraintes protocolaires strictes sont activées et imposent une revue pluridisciplinaire."
        ),
        "Contrefactuel cle:": "Contrefactuel clé:",
        "Si le TRG s'ameliorait a 2 ou moins, l'eligibilite a la surveillance active augmenterait.": (
            "Si le TRG s'améliorait à 2 ou moins, l'éligibilité à la surveillance active augmenterait."
        ),
        "Un TRG superieur a 2 contre-indique la surveillance active.": (
            "Un TRG supérieur à 2 contre-indique la surveillance active."
        ),
    }
    translated = message
    for source, target in replacements.items():
        translated = translated.replace(source, target)
    return translated


def _find_complication_value(items: list[ComplicationRisk], keyword: str, default: float = 0.0) -> float:
    key = keyword.strip().lower()
    for item in items:
        if key in item.name.lower():
            return float(item.value)
    return float(default)


def _confidence_level(score: float) -> str:
    if score >= 75.0:
        return "high"
    if score >= 55.0:
        return "medium"
    return "low"


def _survival_curve_from_map(points: dict[int, float]) -> SurvivalCurve:
    return SurvivalCurve(
        months_1=float(points.get(1, points.get(3, 100.0))),
        months_3=float(points.get(3, points.get(6, 98.0))),
        months_6=float(points.get(6, points.get(12, 95.0))),
        months_12=float(points.get(12, points.get(24, 90.0))),
        months_24=float(points.get(24, points.get(36, 85.0))),
        months_36=float(points.get(36, points.get(60, 80.0))),
        months_60=float(points.get(60, points.get(36, 75.0))),
    )


def _scenario_complication_lines(label: str, scenario: ScenarioResultV4) -> list[str]:
    def _fr_name(name: str) -> str:
        normalized = name.lower()
        mapping = {
            "lars syndrome": "Syndrome LARS",
            "anastomotic leak": "Désunion anastomotique",
            "infectious complication": "Complication infectieuse",
            "urinary dysfunction": "Dysfonction urinaire",
            "stoma-related complication": "Complication liée à la stomie",
            "medical systemic complication": "Complication médicale systémique",
            "local regrowth risk": "Risque de repousse locale",
            "conditional systemic relapse if regrowth": "Risque systémique conditionnel en cas de repousse",
            "surveillance burden": "Charge de surveillance",
            "follow-up anxiety burden": "Anxiété liée au suivi",
        }
        return mapping.get(normalized, name)

    lines: list[str] = []
    if label == "surgery":
        for item in scenario.complications:
            if item.value >= 8.0:
                lines.append(f"{_fr_name(item.name)}: {item.value:.1f}%")
        if not lines:
            lines.append("Complications postopératoires attendues faibles sur ce profil.")
    else:
        for item in scenario.complications:
            if item.value >= 10.0:
                lines.append(f"{_fr_name(item.name)}: {item.value:.1f}%")
        if not lines:
            lines.append("Charge de surveillance modérée sans signal de repousse élevé.")
    return lines


def _to_legacy_scenario(
    scenario: ScenarioResultV4,
    *,
    label: str,
    confidence_score: float,
    missing_inputs: list[str],
) -> ScenarioOutcome:
    stoma_risk = _find_complication_value(scenario.complications, "stoma")
    lars_risk = _find_complication_value(scenario.complications, "lars")
    regrowth = _find_complication_value(scenario.complications, "regrowth", default=scenario.local_recurrence_2y)
    salvage_risk = max(0.0, regrowth * 0.22)

    if scenario.qol_score < 60.0:
        qol_impact = "high"
    elif scenario.qol_score < 75.0:
        qol_impact = "medium"
    else:
        qol_impact = "low"

    if label == "surgery":
        local_recurrence = float(scenario.local_recurrence_5y)
    else:
        local_recurrence = float(scenario.local_recurrence_2y)

    completeness = max(0.0, 100.0 - min(60.0, float(len(missing_inputs) * 4.0)))
    return ScenarioOutcome(
        eligible=bool(scenario.eligible),
        eligibility_score=float(scenario.eligibility_score),
        dfs_2_years=float(scenario.survival_2y),
        dfs_5_years=float(scenario.survival_5y),
        survival_curve=_survival_curve_from_map(scenario.survival_curve),
        local_recurrence_risk=local_recurrence,
        distant_metastasis_risk=float(scenario.distant_metastasis_5y),
        major_complication_risk=float(scenario.major_complication),
        qol_impact=qol_impact,
        qol_score=float(scenario.qol_score),
        stoma_risk=stoma_risk if label == "surgery" else 0.0,
        lars_risk=lars_risk if label == "surgery" else 0.0,
        regrowth_risk=regrowth if label == "watch_and_wait" else 0.0,
        salvage_surgery_risk=salvage_risk if label == "watch_and_wait" else 0.0,
        confidence_level=_confidence_level(confidence_score),
        confidence_score=float(confidence_score),
        data_completeness=completeness,
    )


def _scenario_label_for_v2(recommendation_v4: str) -> str:
    mapping = {
        "surgery": "surgery",
        "watch_wait": "watch_and_wait",
        "multidisciplinary": "uncertain",
    }
    return mapping.get(recommendation_v4, "uncertain")


def _ace_drop_ratio(result: EngineResultV4) -> float:
    baseline = float(result.patient_profile.get("ace_baseline", 0.0))
    current = float(result.patient_profile.get("ace_current", 0.0))
    if baseline <= 0:
        return 0.0
    return _clamp((baseline - current) / baseline, 0.0, 1.0)


def _build_signed_contributions(result: EngineResultV4) -> dict[str, float]:
    """Convention legacy:
    - Valeur positive: favorise Watch & Wait
    - Valeur négative: favorise Chirurgie
    """
    residual_cm = float(result.patient_profile.get("residual_size_cm", 1.0))
    trg = int(result.patient_profile.get("trg", 3))
    crm_status = str(result.patient_profile.get("crm_status", "threatened"))
    frailty_proxy = float(result.feature_contributions.get("Comorbidity_Frailty", 0.0))
    ace_drop = _ace_drop_ratio(result)

    crm_component = {"negative": 8.0, "threatened": -5.0, "positive": -15.0}.get(crm_status, -3.0)
    response_component = (2.0 - float(trg)) * 7.0 + (2.0 - residual_cm) * 9.0
    ace_component = (ace_drop - 0.45) * 26.0
    surgery_control_component = (result.watch_wait.local_recurrence_2y - result.surgery.local_recurrence_5y) * -0.8
    surgery_comp_component = (result.surgery.major_complication - 16.0) * 0.85
    ww_regrowth_component = (result.watch_wait.local_recurrence_2y - 20.0) * -0.9
    frailty_component = (25.0 - frailty_proxy) * -0.45

    raw = {
        "Réponse radiologique (TRG + résidu)": response_component,
        "Marge CRM": crm_component,
        "Cinétique ACE": ace_component,
        "Fragilité médico-chirurgicale": frailty_component,
        "Contrôle local attendu avec chirurgie": surgery_control_component,
        "Risque de complications chirurgicales": surgery_comp_component,
        "Risque de repousse en surveillance": ww_regrowth_component,
    }
    return {name: _clamp(float(value), -45.0, 45.0) for name, value in raw.items()}


def _build_french_alerts(result: EngineResultV4) -> list[str]:
    alerts: list[str] = []
    alerts.extend([_fr(item) for item in list(result.consensus.alerts)])

    cm_stage = str(result.patient_profile.get("cm_stage", "cM0"))
    ecog = int(result.patient_profile.get("ecog", 1))
    age = int(result.patient_profile.get("age", 62))
    asa = int(result.patient_profile.get("asa_score", 2))
    crm_status = str(result.patient_profile.get("crm_status", "threatened"))
    ace_current = float(result.patient_profile.get("ace_current", 0.0))

    if cm_stage == "cM1":
        alerts.append("Stade métastatique cM1: discussion RCP oncologique prioritaire.")
    if ecog >= 4:
        alerts.append("ECOG 4: chirurgie contre-indiquée, discussion palliative recommandée.")
    if age >= 80 and asa >= 3:
        alerts.append("Profil gériatrique fragile (âge >= 80 et ASA >= 3): évaluation gériatrique formalisée recommandée.")
    if crm_status == "positive":
        alerts.append("CRM positif (< 1 mm): risque de marge envahie, privilégier contrôle local maximal.")
    if ace_current > 5.0:
        alerts.append("ACE persistante élevée (> 5 ng/mL): vigilance sur la maladie résiduelle systémique.")
    if result.watch_wait.local_recurrence_2y > 30.0:
        alerts.append("Risque de repousse locale élevé en surveillance active (> 30% à 2 ans).")
    if result.surgery.major_complication > 25.0:
        alerts.append("Risque de complications majeures postopératoires élevé.")

    for invariant in result.safety.invariants:
        if not invariant.passed:
            alerts.append(f"Invariant de sécurité non respecté: {invariant.message}")

    alerts = list(dict.fromkeys(alerts))
    if not alerts:
        alerts.append("Aucune alerte clinique majeure détectée sur ce profil.")
    return alerts


def _build_primary_factors_french(result: EngineResultV4) -> list[tuple[str, float, str]]:
    mapped: list[tuple[str, float, str]] = []
    rename = {
        "Radiology signal": "Signal radiologique",
        "Biology signal": "Signal biologique",
        "Surgery R0": "Probabilité de résection R0",
        "Frailty": "Fragilité globale",
    }
    for name, weight, description in result.primary_factors:
        mapped.append((rename.get(str(name), str(name)), float(weight), str(description)))
    return mapped


def _format_percent(value: float) -> str:
    return f"{float(value):.0f}%"


def _build_response_sentence(result: EngineResultV4) -> str:
    profile = result.patient_profile
    clinical_response = str(profile.get("clinical_response", "partial")).lower()
    residual_cm = float(profile.get("residual_size_cm", 0.0))
    ace_baseline = float(profile.get("ace_baseline", 0.0))
    ace_current = float(profile.get("ace_current", 0.0))

    if clinical_response == "complete":
        sentence = "La tumeur paraît avoir très bien répondu au traitement."
    elif clinical_response == "near_complete":
        sentence = "La réponse au traitement paraît très favorable."
    elif clinical_response == "partial":
        sentence = "La réponse au traitement reste partielle."
    else:
        sentence = "La réponse au traitement reste insuffisante."

    if residual_cm > 0.0:
        sentence = sentence[:-1] + f", avec une lésion résiduelle estimée à {residual_cm:.1f} cm."

    if ace_baseline > 0.0 and ace_current > 0.0:
        ace_drop = (ace_baseline - ace_current) / ace_baseline
        if ace_drop >= 0.5:
            sentence += f" Le marqueur ACE a baissé d'environ {ace_drop * 100.0:.0f}%, ce qui est rassurant."
        elif ace_current > ace_baseline * 1.1:
            sentence += " Le marqueur ACE est remonté, ce qui appelle à la prudence."
        elif ace_current > 5.0:
            sentence += " Le marqueur ACE reste élevé et justifie une vigilance supplémentaire."

    return sentence


def _build_patient_friendly_summary(result: EngineResultV4) -> str:
    recommendation = str(result.consensus.recommendation)
    surgery = result.surgery
    watch_wait = result.watch_wait
    response_sentence = _build_response_sentence(result)

    if recommendation == "watch_wait":
        surveillance_load = _find_complication_value(watch_wait.complications, "surveillance", default=45.0)
        burden_sentence = (
            "Cette option demande un suivi très régulier par IRM, endoscopie et consultation."
            if surveillance_load >= 55.0
            else "Cette option reste possible à condition d'accepter un suivi régulier."
        )
        return " ".join(
            [
                "Au vu des données actuelles, une surveillance active sans chirurgie immédiate semble être l'option la plus adaptée.",
                response_sentence,
                (
                    f"Dans ce scénario, le risque de repousse locale à 2 ans est estimé à "
                    f"{_format_percent(watch_wait.local_recurrence_2y)} et la chance de rester sans rechute à 5 ans "
                    f"à {_format_percent(watch_wait.survival_5y)}."
                ),
                burden_sentence,
            ]
        )

    if recommendation == "surgery":
        lars_risk = _find_complication_value(surgery.complications, "lars", default=surgery.major_complication)
        impact_sentence = (
            f"Le principal inconvénient est un risque de complication importante d'environ {_format_percent(surgery.major_complication)}, "
            f"avec un risque de troubles digestifs durables estimé à {_format_percent(lars_risk)}."
        )
        return " ".join(
            [
                "Au vu des données actuelles, la chirurgie semble être l'option la plus sûre pour mieux contrôler la maladie.",
                response_sentence,
                (
                    f"Dans ce scénario, la chance de rester sans rechute à 5 ans est estimée à "
                    f"{_format_percent(surgery.survival_5y)} et le risque de récidive locale à 5 ans à "
                    f"{_format_percent(surgery.local_recurrence_5y)}."
                ),
                impact_sentence,
            ]
        )

    return " ".join(
        [
            "Les données actuelles ne permettent pas de privilégier clairement une seule option de traitement.",
            response_sentence,
            (
                f"La chirurgie offrirait une chance de rester sans rechute à 5 ans d'environ "
                f"{_format_percent(surgery.survival_5y)}, tandis que la surveillance active exposerait à un risque "
                f"de repousse locale d'environ {_format_percent(watch_wait.local_recurrence_2y)} à 2 ans."
            ),
            "Une discussion détaillée avec l'équipe soignante est nécessaire pour choisir l'option la plus adaptée.",
        ]
    )


def _build_legacy_rationale(result: EngineResultV4, recommended_scenario: str) -> ClinicalRationale:
    primary = _build_primary_factors_french(result)

    signed = _build_signed_contributions(result)
    secondary = [
        (name, abs(float(value)) / 100.0, "Contribution directionnelle au consensus")
        for name, value in sorted(signed.items(), key=lambda item: abs(float(item[1])), reverse=True)[3:8]
    ]

    surgery_benefits = [
        f"Probabilité R0: {result.surgery.r0_probability:.1f}%",
        f"DFS à 5 ans: {result.surgery.survival_5y:.1f}%",
    ]
    surgery_risks = [
        f"Complications majeures: {result.surgery.major_complication:.1f}%",
        f"Récidive locale à 5 ans: {result.surgery.local_recurrence_5y:.1f}%",
    ] + _scenario_complication_lines("surgery", result.surgery)

    ww_benefits = [
        f"Score d'éligibilité: {result.watch_wait.eligibility_score:.1f}/100",
        f"Qualité de vie projetée: {result.watch_wait.qol_score:.1f}/100",
    ]
    ww_risks = [
        f"Repousse locale à 2 ans: {result.watch_wait.local_recurrence_2y:.1f}%",
        f"Métastases à 5 ans: {result.watch_wait.distant_metastasis_5y:.1f}%",
    ] + _scenario_complication_lines("watch_and_wait", result.watch_wait)

    strength = str(result.consensus.recommendation_strength)
    if strength not in {"strong", "moderate", "weak"}:
        strength = "moderate"

    recommendation_text = _fr(str(result.consensus.rationale))
    if result.consensus.counterfactuals:
        recommendation_text = f"{recommendation_text} Contrefactuel clé: {_fr(result.consensus.counterfactuals[0])}"

    return ClinicalRationale(
        primary_factors=primary,
        secondary_factors=secondary,
        surgery_benefits=surgery_benefits,
        surgery_risks=surgery_risks,
        ww_benefits=ww_benefits,
        ww_risks=ww_risks,
        recommended_scenario=recommended_scenario,
        recommendation_strength=strength,
        recommendation_text=recommendation_text,
        feature_contributions=signed,
        clinical_alerts=_build_french_alerts(result),
    )


def _build_synthetic_llm_response(result: EngineResultV4) -> MedicalLLMResponse:
    surgery = SurgeryEstimates(
        recurrence_local_2y=float(result.surgery.local_recurrence_2y),
        recurrence_local_5y=float(result.surgery.local_recurrence_5y),
        recurrence_systemic_2y=float(result.surgery.distant_metastasis_5y * 0.45),
        survival_dfs_2y=float(result.surgery.survival_2y),
        survival_dfs_5y=float(result.surgery.survival_5y),
        complication_rate=float(result.surgery.major_complication),
        lars_risk=_find_complication_value(result.surgery.complications, "lars"),
        colostomy_risk=_find_complication_value(result.surgery.complications, "stoma"),
        r0_probability=float(result.surgery.r0_probability),
        narrative_fr="Synthèse multi-agent assistée par le module LLM.",
    )
    watch_wait = WatchWaitEstimates(
        regrowth_2y=float(result.watch_wait.local_recurrence_2y),
        regrowth_5y=float(result.watch_wait.local_recurrence_5y),
        salvage_surgery_success=float(max(0.0, 100.0 - result.watch_wait.local_recurrence_2y * 0.55)),
        systemic_relapse_if_regrowth=_find_complication_value(
            result.watch_wait.complications, "conditional systemic relapse"
        ),
        survival_dfs_2y=float(result.watch_wait.survival_2y),
        survival_dfs_5y=float(result.watch_wait.survival_5y),
        organ_preservation_2y=float(max(0.0, 100.0 - result.watch_wait.local_recurrence_2y)),
        surveillance_burden="high"
        if _find_complication_value(result.watch_wait.complications, "surveillance") >= 60
        else "moderate",
        narrative_fr="Synthèse multi-agent assistée par le module LLM.",
    )
    key_factors = [
        KeyFactor(
            factor=str(name),
            value=f"{float(weight):.2f}",
            direction="favorable" if float(weight) >= 0.5 else "neutral",
            impact_magnitude=max(-1.0, min(1.0, float(weight))),
            evidence_source=str(description),
        )
        for name, weight, description in _build_primary_factors_french(result)[:5]
    ]
    uncertainty = "low" if result.consensus.confidence >= 80 else "moderate" if result.consensus.confidence >= 60 else "high"
    return MedicalLLMResponse(
        surgery=surgery,
        watch_wait=watch_wait,
        recommendation=result.consensus.recommendation,
        recommendation_rationale=_fr(result.consensus.rationale),
        uncertainty_level=uncertainty,
        uncertainty_reason=f"Niveau de désaccord: {result.consensus.disagreement_level}",
        clinical_alerts=_build_french_alerts(result),
        key_factors=key_factors,
        patient_friendly_summary=_build_patient_friendly_summary(result),
    )


def to_legacy_decision_result(patient_input: PatientInput, result: EngineResultV4) -> DecisionResult:
    crf_input = map_patient_input_to_crf(patient_input)
    recommended = _scenario_label_for_v2(result.consensus.recommendation)
    confidence_score = float(result.consensus.confidence)
    missing_inputs = list(result.patient_profile.missing_inputs)

    surgery_outcome = _to_legacy_scenario(
        result.surgery,
        label="surgery",
        confidence_score=confidence_score,
        missing_inputs=missing_inputs,
    )
    ww_outcome = _to_legacy_scenario(
        result.watch_wait,
        label="watch_and_wait",
        confidence_score=confidence_score,
        missing_inputs=missing_inputs,
    )
    rationale = _build_legacy_rationale(result, recommended)

    llm_source = result.mode_runtime in {"openai", "alt_llm"}
    llm_response = _build_synthetic_llm_response(result) if llm_source else None

    return DecisionResult(
        patient_input=patient_input,
        crf_input=crf_input,
        surgery_outcome=surgery_outcome,
        ww_outcome=ww_outcome,
        rationale=rationale,
        recommended_scenario=recommended,
        recommendation_strength=rationale.recommendation_strength,
        llm_source=llm_source,
        llm_response=llm_response,
    )


class LegacyUIEngine:
    """Pont entre UI historique et moteur v4."""

    def __init__(self) -> None:
        self.v4 = BrainEngineV4()

    def run_decision(self, patient_input: PatientInput) -> DecisionResult:
        result_v4 = self.v4.run_decision(patient_input)
        return to_legacy_decision_result(patient_input, result_v4)

    def run_dataset_row(self, row: dict[str, Any]) -> DecisionResult:
        profile_result = self.v4.run_dataset_row(row)
        patient_input = PatientInput(
            ct_stage=str(profile_result.patient_profile.get("ct_stage", "cT3")),
            cn_stage=str(profile_result.patient_profile.get("cn_stage", "cN0")),
            cm_stage=str(profile_result.patient_profile.get("cm_stage", "cM0")),
            ace_baseline=float(profile_result.patient_profile.get("ace_baseline", 8.0)),
            ace_current=float(profile_result.patient_profile.get("ace_current", 3.0)),
            residual_tumor_ratio=float(profile_result.patient_profile.get("residual_tumor_ratio", 20.0)),
            imaging_quality=str(profile_result.patient_profile.get("imaging_quality", "Moyenne")),
            age=int(profile_result.patient_profile.get("age", 62)),
            performance_status=int(profile_result.patient_profile.get("ecog", 1)),
            residual_size_cm=float(profile_result.patient_profile.get("residual_size_cm", 1.0)),
            mrtrg=int(profile_result.patient_profile.get("trg", 3)),
            crm_distance_mm=float(profile_result.patient_profile.get("crm_distance_mm", 5.0)),
        )
        return to_legacy_decision_result(patient_input, profile_result)
