from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Dict, List, TypedDict

TNM_T_SCORES = {"cT1": 0.15, "cT2": 0.35, "cT3": 0.65, "cT4": 0.9}
TNM_N_SCORES = {"cN0": 0.15, "cN1": 0.55, "cN2": 0.8}
TNM_M_SCORES = {"cM0": 0.0, "cM1": 1.0}

ACE_ALERT_THRESHOLD = 5.0
ACE_HIGH_ALERT_THRESHOLD = 10.0
ACE_DROP_LOW_THRESHOLD = 30.0
RESIDUAL_ALERT_THRESHOLD = 30.0


class PatientInput(TypedDict):
    ct_stage: str
    cn_stage: str
    cm_stage: str
    ace_baseline: float
    ace_current: float
    residual_tumor_ratio: float
    imaging_quality: str
    age: int
    performance_status: int


class RadiologyResult(TypedDict):
    local_recurrence_risk: float
    radiology_confidence: float
    residual_component: float
    summary: str


class BiologyResult(TypedDict):
    bio_risk: float
    ace_drop_pct: float
    normalized_current_cea: float
    summary: str


class ScenarioResult(TypedDict):
    risk: float
    qol_impact: float
    confidence: float


class CoordinatorResult(TypedDict):
    recurrence_probability: float
    recommendation: str
    rationale: str
    uncertainty_level: str
    conflict_detected: bool
    conflict_reasons: List[str]
    clinical_alerts: List[str]
    rule_flags: Dict[str, bool]
    scenario_surgery: ScenarioResult
    scenario_watch_wait: ScenarioResult
    feature_values: Dict[str, float]
    shap_like: Dict[str, float]


class DecisionPack(TypedDict):
    patient: PatientProfile
    radiology: RadiologyResult
    biology: BiologyResult
    coordinator: CoordinatorResult


@dataclass
class PatientProfile:
    ct_stage: str
    cn_stage: str
    cm_stage: str
    ace_baseline: float
    ace_current: float
    residual_tumor_ratio: float
    imaging_quality: str
    age: int
    performance_status: int


class RadiologistAgent:
    def analyze(self, patient: PatientProfile) -> RadiologyResult:
        t_risk = TNM_T_SCORES.get(patient.ct_stage, 0.5)
        n_risk = TNM_N_SCORES.get(patient.cn_stage, 0.5)
        m_risk = TNM_M_SCORES.get(patient.cm_stage, 0.0)

        residual_component = min(max(patient.residual_tumor_ratio / 100.0, 0.0), 1.0)
        quality_bonus = 0.05 if patient.imaging_quality == "Elevee" else 0.0

        raw = 0.38 * t_risk + 0.24 * n_risk + 0.20 * residual_component + 0.18 * m_risk
        local_recurrence_risk = min(max(raw, 0.0), 1.0)
        confidence = min(max(0.72 + quality_bonus - (0.08 if patient.cm_stage == "cM1" else 0.0), 0.55), 0.95)

        return {
            "local_recurrence_risk": local_recurrence_risk,
            "radiology_confidence": confidence,
            "residual_component": residual_component,
            "summary": "Risque radiologique eleve" if local_recurrence_risk >= 0.65 else "Risque radiologique modere",
        }


class BiologistAgent:
    def analyze(self, patient: PatientProfile) -> BiologyResult:
        baseline = max(patient.ace_baseline, 0.1)
        current = max(patient.ace_current, 0.0)

        drop_pct = ((baseline - current) / baseline) * 100.0
        normalized_current = min(current / 25.0, 1.0)

        if drop_pct >= 60:
            kinetics_label = "Reponse biologique favorable"
            kinetics_risk = 0.2
        elif drop_pct >= 30:
            kinetics_label = "Reponse biologique intermediaire"
            kinetics_risk = 0.45
        else:
            kinetics_label = "Reponse biologique insuffisante"
            kinetics_risk = 0.75

        bio_risk = min(max(0.58 * normalized_current + 0.42 * kinetics_risk, 0.0), 1.0)

        return {
            "bio_risk": bio_risk,
            "ace_drop_pct": drop_pct,
            "normalized_current_cea": normalized_current,
            "summary": kinetics_label,
        }


class CoordinatorAgent:
    def synthesize(
        self,
        patient: PatientProfile,
        radiology: RadiologyResult,
        biology: BiologyResult,
    ) -> CoordinatorResult:
        age_factor = min(max((patient.age - 35) / 55.0, 0.0), 1.0)
        ps_factor = min(max(patient.performance_status / 4.0, 0.0), 1.0)
        metastatic_flag = 1.0 if patient.cm_stage == "cM1" else 0.0

        linear_risk = (
            1.20 * float(radiology["local_recurrence_risk"])
            + 1.05 * float(biology["bio_risk"])
            + 0.35 * age_factor
            + 0.25 * ps_factor
            + 0.85 * metastatic_flag
            - 1.55
        )
        recurrence_probability = 1.0 / (1.0 + math.exp(-linear_risk))

        surgery_risk = min(max(recurrence_probability * 0.76, 0.01), 0.95)
        wnw_risk = min(max(recurrence_probability * 1.10, 0.01), 0.98)

        surgery_qol_impact = 0.58
        wnw_qol_impact = 0.26

        ace_alert = patient.ace_current > ACE_ALERT_THRESHOLD
        ace_high_alert = patient.ace_current >= ACE_HIGH_ALERT_THRESHOLD
        ace_drop_low = float(biology["ace_drop_pct"]) < ACE_DROP_LOW_THRESHOLD
        residual_alert = patient.residual_tumor_ratio > RESIDUAL_ALERT_THRESHOLD
        tnm_high_alert = patient.ct_stage == "cT4" or patient.cn_stage == "cN2" or patient.cm_stage == "cM1"

        radio_favorable = float(radiology["local_recurrence_risk"]) < 0.40 and patient.residual_tumor_ratio < 20.0
        bio_unfavorable = float(biology["bio_risk"]) >= 0.60 or (ace_alert and ace_drop_low)

        conflict_reasons: List[str] = []
        if radio_favorable and bio_unfavorable:
            conflict_reasons.append("Imagerie plutot favorable mais signal biologique defavorable")
        if float(radiology["local_recurrence_risk"]) >= 0.65 and float(biology["bio_risk"]) <= 0.35:
            conflict_reasons.append("Risque radiologique eleve avec profil biologique favorable")
        if patient.imaging_quality == "Moyenne" and float(radiology["local_recurrence_risk"]) < 0.45:
            conflict_reasons.append("Qualite d'imagerie moyenne limitant la confiance de l'interpretation")

        clinical_alerts: List[str] = []
        if tnm_high_alert:
            clinical_alerts.append("Alerte TNM (cT4/cN2/cM1)")
        if residual_alert:
            clinical_alerts.append("Alerte residu tumoral > 30%")
        if ace_alert:
            clinical_alerts.append("Alerte ACE > 5 ng/mL")
        if ace_high_alert:
            clinical_alerts.append("Alerte ACE >= 10 ng/mL")
        if ace_drop_low:
            clinical_alerts.append("Baisse ACE < 30%")

        conflict_detected = len(conflict_reasons) > 0
        uncertainty_score = 0
        if conflict_detected:
            uncertainty_score += 2
        if patient.imaging_quality == "Moyenne":
            uncertainty_score += 1
        if patient.cm_stage == "cM1":
            uncertainty_score += 1

        if uncertainty_score >= 3:
            uncertainty_level = "Elevee"
        elif uncertainty_score >= 1:
            uncertainty_level = "Moyenne"
        else:
            uncertainty_level = "Faible"

        if patient.cm_stage == "cM1":
            recommendation = "Chirurgie Radicale"
            rationale = "Presence de cM1: priorite a une strategie oncologique de controle maximal et reevaluation multidisciplinaire."
        elif tnm_high_alert or residual_alert or (ace_alert and ace_drop_low):
            recommendation = "Chirurgie Radicale"
            rationale = "Regles cliniques d'alerte activees (TNM/ACE/residu), orientant vers un controle local maximal."
        elif wnw_risk < 0.30 and float(radiology["local_recurrence_risk"]) < 0.60 and not ace_alert:
            recommendation = "Watch and Wait"
            rationale = "Profil global favorable avec risque de recidive contenu et cinetique biologique rassurante."
        elif recurrence_probability < 0.34 and not ace_high_alert:
            recommendation = "Watch and Wait"
            rationale = "Probabilite de recidive basse, surveillance active envisageable sous controle strict."
        else:
            recommendation = "Chirurgie Radicale"
            rationale = "Le profil combine suggere un risque de recidive justifiant un controle local maximal."

        if uncertainty_level == "Elevee":
            rationale += " Incerte forte: reevaluation rapprochee et discussion RCP renforcee recommandees."

        confidence_penalty = 0.12 if uncertainty_level == "Elevee" else (0.06 if uncertainty_level == "Moyenne" else 0.0)

        features = {
            "cT_stage_weight": float(TNM_T_SCORES.get(patient.ct_stage, 0.5)),
            "cN_stage_weight": float(TNM_N_SCORES.get(patient.cn_stage, 0.5)),
            "Residual_tumor_ratio": float(patient.residual_tumor_ratio / 100.0),
            "CEA_current": float(patient.ace_current / 25.0),
            "CEA_drop": float(max(0.0, (patient.ace_baseline - patient.ace_current) / max(patient.ace_baseline, 0.1))),
            "Performance_status": float(ps_factor),
        }

        shap_like = {
            "cT_stage_weight": round((features["cT_stage_weight"] - 0.4) * 0.28, 3),
            "cN_stage_weight": round((features["cN_stage_weight"] - 0.3) * 0.22, 3),
            "Residual_tumor_ratio": round((features["Residual_tumor_ratio"] - 0.25) * 0.18, 3),
            "CEA_current": round((features["CEA_current"] - 0.18) * 0.20, 3),
            "CEA_drop": round((0.5 - features["CEA_drop"]) * 0.15, 3),
            "Performance_status": round((features["Performance_status"] - 0.2) * 0.10, 3),
        }

        return {
            "recurrence_probability": recurrence_probability,
            "recommendation": recommendation,
            "rationale": rationale,
            "uncertainty_level": uncertainty_level,
            "conflict_detected": conflict_detected,
            "conflict_reasons": conflict_reasons,
            "clinical_alerts": clinical_alerts,
            "rule_flags": {
                "tnm_high_alert": tnm_high_alert,
                "ace_alert": ace_alert,
                "ace_high_alert": ace_high_alert,
                "ace_drop_low": ace_drop_low,
                "residual_alert": residual_alert,
                "conflict_detected": conflict_detected,
            },
            "scenario_surgery": {
                "risk": surgery_risk,
                "qol_impact": surgery_qol_impact,
                "confidence": min(max(float(radiology["radiology_confidence"] * 0.5 + 0.4 - confidence_penalty), 0.35), 0.98),
            },
            "scenario_watch_wait": {
                "risk": wnw_risk,
                "qol_impact": wnw_qol_impact,
                "confidence": min(max(float(radiology["radiology_confidence"] * 0.5 + 0.38 - confidence_penalty), 0.32), 0.98),
            },
            "feature_values": features,
            "shap_like": shap_like,
        }


def run_multimodal_pipeline(patient_data: PatientInput) -> DecisionPack:
    patient = PatientProfile(
        ct_stage=str(patient_data["ct_stage"]),
        cn_stage=str(patient_data["cn_stage"]),
        cm_stage=str(patient_data["cm_stage"]),
        ace_baseline=float(patient_data["ace_baseline"]),
        ace_current=float(patient_data["ace_current"]),
        residual_tumor_ratio=float(patient_data["residual_tumor_ratio"]),
        imaging_quality=str(patient_data["imaging_quality"]),
        age=int(patient_data["age"]),
        performance_status=int(patient_data["performance_status"]),
    )

    radiology_agent = RadiologistAgent()
    biology_agent = BiologistAgent()
    coordinator = CoordinatorAgent()

    radiology_result = radiology_agent.analyze(patient)
    biology_result = biology_agent.analyze(patient)
    coordinator_result = coordinator.synthesize(patient, radiology_result, biology_result)

    return {
        "patient": patient,
        "radiology": radiology_result,
        "biology": biology_result,
        "coordinator": coordinator_result,
    }


def explain_recommendation_chat(question: str, decision_pack: DecisionPack) -> str:
    q = question.lower().strip()
    coordinator = decision_pack["coordinator"]
    radiology = decision_pack["radiology"]
    biology = decision_pack["biology"]

    if "pourquoi" in q and "surveillance" in q:
        return (
            "La surveillance est favorisee quand le risque estime de recidive reste bas, "
            f"ici {coordinator['scenario_watch_wait']['risk'] * 100:.1f}%, "
            "avec une cinetique ACE favorable et un residu tumoral controle."
        )

    if "pourquoi" in q and "chirurgie" in q:
        return (
            "La chirurgie est privilegiee lorsque le risque combine radiologie + biologie est eleve. "
            f"Risque radiologique: {radiology['local_recurrence_risk'] * 100:.1f}%, "
            f"risque biologique: {biology['bio_risk'] * 100:.1f}%."
        )

    if "ace" in q or "cea" in q:
        return (
            f"La baisse de l'ACE est de {biology['ace_drop_pct']:.1f}%. "
            "Une baisse marquee est associee a une reduction du risque de recidive."
        )

    if "confiance" in q:
        return (
            f"La confiance radiologique est estimee a {radiology['radiology_confidence'] * 100:.1f}%. "
            f"Niveau d'incertitude global: {coordinator['uncertainty_level']}."
        )

    if "incertitude" in q or "conflit" in q:
        if coordinator["conflict_detected"]:
            reasons = "; ".join(coordinator["conflict_reasons"])
            return (
                f"Incertitude {coordinator['uncertainty_level']}. "
                f"Conflits detectes: {reasons}."
            )
        return f"Aucun conflit majeur detecte. Niveau d'incertitude: {coordinator['uncertainty_level']}."

    return (
        "Le modele combine stades cTNM, residu tumoral et dynamique ACE pour estimer la recidive. "
        f"Recommendation actuelle: {coordinator['recommendation']} (incertitude {coordinator['uncertainty_level']})."
    )


def render_decision_lines(decision_pack: DecisionPack) -> List[str]:
    coordinator = decision_pack["coordinator"]
    radiology = decision_pack["radiology"]
    biology = decision_pack["biology"]

    return [
        "PREDI-Care - Resume de decision clinique",
        f"Recommendation finale: {coordinator['recommendation']}",
        f"Probabilite globale de recidive: {coordinator['recurrence_probability'] * 100:.1f}%",
        f"Niveau d'incertitude: {coordinator['uncertainty_level']}",
        f"Conflit detecte: {'Oui' if coordinator['conflict_detected'] else 'Non'}",
        f"Scenario Chirurgie - risque: {coordinator['scenario_surgery']['risk'] * 100:.1f}%",
        f"Scenario Watch and Wait - risque: {coordinator['scenario_watch_wait']['risk'] * 100:.1f}%",
        f"Risque radiologique: {radiology['local_recurrence_risk'] * 100:.1f}%",
        f"Risque biologique: {biology['bio_risk'] * 100:.1f}%",
        f"Baisse ACE: {biology['ace_drop_pct']:.1f}%",
        f"Alertes cliniques: {', '.join(coordinator['clinical_alerts']) if coordinator['clinical_alerts'] else 'Aucune'}",
        f"Rationale: {coordinator['rationale']}",
    ]
