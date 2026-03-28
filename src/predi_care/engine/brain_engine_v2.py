"""Brain Engine V2 - LLM-Powered Clinical Decision Engine with Heuristic Fallback.

Integrates NVIDIA NIM LLM with the existing CRFSimulator architecture.
When the LLM call succeeds, its calibrated medical reasoning is used.
On failure, the engine falls back to the existing heuristic CRFSimulator.

Version: 3.0 — LLM Integration
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Any, Optional, List

from predi_care.engine.patient_types import PatientInput
from predi_care.engine.crf_simulator import (
    CRFSimulator,
    CRFInput,
    ScenarioOutcome,
    SurvivalCurve,
    ClinicalRationale,
)
from predi_care.engine.crf_mapper import map_patient_input_to_crf
from predi_care.engine.llm_client import (
    MedicalLLMResponse,
    call_medical_llm,
)

logger = logging.getLogger(__name__)


@dataclass
class DecisionResult:
    """Complete decision output including both scenarios and rationale.

    This is the main output structure consumed by the UI.
    """

    # === Input Data ===
    patient_input: PatientInput
    crf_input: CRFInput

    # === Scenario Outcomes ===
    surgery_outcome: ScenarioOutcome
    ww_outcome: ScenarioOutcome

    # === Rationale ===
    rationale: ClinicalRationale

    # === Recommendation Summary ===
    recommended_scenario: str   # "surgery", "watch_and_wait", "uncertain"
    recommendation_strength: str  # "strong", "moderate", "weak"

    # === LLM metadata ===
    llm_source: bool = False   # True = LLM, False = heuristic fallback
    llm_response: Optional[MedicalLLMResponse] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "surgery": {
                "eligible": self.surgery_outcome.eligible,
                "eligibility_score": self.surgery_outcome.eligibility_score,
                "dfs_2y": self.surgery_outcome.dfs_2_years,
                "dfs_5y": self.surgery_outcome.dfs_5_years,
                "survival_curve": self.surgery_outcome.survival_curve.to_dict(),
                "local_recurrence_risk": self.surgery_outcome.local_recurrence_risk,
                "distant_metastasis_risk": self.surgery_outcome.distant_metastasis_risk,
                "major_complication_risk": self.surgery_outcome.major_complication_risk,
                "qol_score": self.surgery_outcome.qol_score,
                "stoma_risk": self.surgery_outcome.stoma_risk,
                "lars_risk": self.surgery_outcome.lars_risk,
                "confidence_score": self.surgery_outcome.confidence_score,
                "confidence_level": self.surgery_outcome.confidence_level,
            },
            "watch_and_wait": {
                "eligible": self.ww_outcome.eligible,
                "eligibility_score": self.ww_outcome.eligibility_score,
                "dfs_2y": self.ww_outcome.dfs_2_years,
                "dfs_5y": self.ww_outcome.dfs_5_years,
                "survival_curve": self.ww_outcome.survival_curve.to_dict(),
                "local_recurrence_risk": self.ww_outcome.local_recurrence_risk,
                "distant_metastasis_risk": self.ww_outcome.distant_metastasis_risk,
                "regrowth_risk": self.ww_outcome.regrowth_risk,
                "salvage_surgery_risk": self.ww_outcome.salvage_surgery_risk,
                "qol_score": self.ww_outcome.qol_score,
                "confidence_score": self.ww_outcome.confidence_score,
                "confidence_level": self.ww_outcome.confidence_level,
            },
            "recommendation": {
                "scenario": self.recommended_scenario,
                "strength": self.recommendation_strength,
                "text": self.rationale.recommendation_text,
                "primary_factors": [
                    {"variable": var, "weight": weight, "description": desc}
                    for var, weight, desc in self.rationale.primary_factors
                ],
                "feature_contributions": self.rationale.feature_contributions,
                "clinical_alerts": self.rationale.clinical_alerts,
            },
            "comparison": {
                "surgery_benefits": self.rationale.surgery_benefits,
                "surgery_risks": self.rationale.surgery_risks,
                "ww_benefits": self.rationale.ww_benefits,
                "ww_risks": self.rationale.ww_risks,
            },
            "llm_source": self.llm_source,
        }


# ---------------------------------------------------------------------------
# Helper: build the patient context dict for the LLM
# ---------------------------------------------------------------------------

def _build_patient_context(patient: PatientInput) -> Dict[str, Any]:
    """Build the structured patient context dict expected by the LLM."""

    # Extract cT number from "cT3" → 3
    ct_num = int(patient["ct_stage"].replace("cT", "")) if patient["ct_stage"].startswith("cT") else 2
    cn_num = int(patient["cn_stage"].replace("cN", "")) if patient["cn_stage"].startswith("cN") else 0
    cm_num = int(patient["cm_stage"].replace("cM", "")) if patient["cm_stage"].startswith("cM") else 0

    # Derive residual size in cm from ratio (rough: 0-100% → 0-5cm)
    residual_cm = round(patient["residual_tumor_ratio"] / 20.0, 1)

    # Derive TRG Rödel from residual ratio
    ratio = patient["residual_tumor_ratio"]
    if ratio == 0:
        trg = 4  # Complete regression
    elif ratio < 10:
        trg = 3  # >50% regression
    elif ratio < 50:
        trg = 2  # 25-50% regression
    elif ratio < 80:
        trg = 1
    else:
        trg = 0

    # Derive clinical response from residual
    if ratio == 0:
        clin_resp = "complete"
    elif ratio < 10:
        clin_resp = "subcomplete"
    elif ratio < 30:
        clin_resp = "partial"
    else:
        clin_resp = "non_determined"

    return {
        "clinical": {
            "cT": ct_num,
            "cN": cn_num,
            "cM": cm_num,
            "age": patient["age"],
            "ecog": patient["performance_status"],
            "sphincter_preserved": True,
            "distance_marge_anale": patient.get("distance_marge_anale", 8.0),
        },
        "response": {
            "residual_size_cm": residual_cm,
            "trg_rodel": trg,
            "clinical_response_tr": clin_resp,
            "delay_weeks_post_rct": patient.get("delay_weeks_post_rct", 8),
            "protocol_neoadjuvant": patient.get("protocol_neoadjuvant", "RCT standard"),
        },
        "imaging": {
            "crm_mm": 5.0 if ratio < 30 else (1.5 if ratio < 60 else 0.5),
            "emvi": patient.get("emvi", False),
            "mrtrg": patient.get("mrtrg", 3),
            "mri_quality": "good" if patient["imaging_quality"] == "Elevee" else "moderate",
        },
        "biology": {
            "ace_baseline": patient["ace_baseline"],
            "ace_current": patient["ace_current"],
            "hemoglobin": patient.get("hemoglobin", 13.5),
            "albumin": patient.get("albumin", 40.0),
            "nlr_ratio": 2.5,
            "msi_status": patient.get("msi_status", "Non testé"),
        },
        "comorbidities": {
            "asa_score": patient.get("asa_score", 1),
            "smoking": patient.get("smoking", False),
            "diabetes": patient.get("diabetes", False),
            "bmi": 25,
        },
    }


# ---------------------------------------------------------------------------
# Helper: convert MedicalLLMResponse → ScenarioOutcome + ClinicalRationale
# ---------------------------------------------------------------------------

def _llm_to_surgery_outcome(llm: MedicalLLMResponse) -> ScenarioOutcome:
    """Map LLM surgery estimates to a ScenarioOutcome."""
    s = llm.surgery
    dfs_2y = s.survival_dfs_2y
    dfs_5y = s.survival_dfs_5y

    return ScenarioOutcome(
        eligible=True,
        eligibility_score=100.0,
        dfs_2_years=dfs_2y,
        dfs_5_years=dfs_5y,
        survival_curve=_build_curve(dfs_2y, dfs_5y, "surgery"),
        local_recurrence_risk=s.recurrence_local_5y,
        distant_metastasis_risk=s.recurrence_systemic_2y,
        major_complication_risk=s.complication_rate,
        qol_impact="high" if s.lars_risk > 40 else "medium" if s.lars_risk > 20 else "low",
        qol_score=max(40.0, 100.0 - s.lars_risk - s.colostomy_risk * 0.3),
        stoma_risk=s.colostomy_risk,
        lars_risk=s.lars_risk,
        regrowth_risk=0.0,
        salvage_surgery_risk=0.0,
        confidence_level="high" if llm.uncertainty_level == "low" else "medium" if llm.uncertainty_level == "moderate" else "low",
        confidence_score=85.0 if llm.uncertainty_level == "low" else 65.0 if llm.uncertainty_level == "moderate" else 45.0,
        data_completeness=100.0,
    )


def _llm_to_ww_outcome(llm: MedicalLLMResponse) -> ScenarioOutcome:
    """Map LLM W&W estimates to a ScenarioOutcome."""
    w = llm.watch_wait
    dfs_2y = w.survival_dfs_2y
    dfs_5y = w.survival_dfs_5y
    eligible = llm.recommendation != "surgery"

    return ScenarioOutcome(
        eligible=eligible,
        eligibility_score=w.organ_preservation_2y,
        dfs_2_years=dfs_2y,
        dfs_5_years=dfs_5y,
        survival_curve=_build_curve(dfs_2y, dfs_5y, "watch_and_wait"),
        local_recurrence_risk=w.regrowth_2y * 0.2,
        distant_metastasis_risk=w.systemic_relapse_if_regrowth * w.regrowth_2y / 100.0,
        major_complication_risk=2.0,
        qol_impact="low",
        qol_score=min(100.0, 95.0 - (100.0 - w.organ_preservation_2y) * 0.2),
        stoma_risk=0.0,
        lars_risk=0.0,
        regrowth_risk=w.regrowth_2y,
        salvage_surgery_risk=w.regrowth_2y * (1.0 - w.salvage_surgery_success / 100.0) if w.regrowth_2y > 0 else 0.0,
        confidence_level="high" if llm.uncertainty_level == "low" else "medium" if llm.uncertainty_level == "moderate" else "low",
        confidence_score=80.0 if llm.uncertainty_level == "low" else 60.0 if llm.uncertainty_level == "moderate" else 40.0,
        data_completeness=100.0,
    )


def _llm_to_rationale(llm: MedicalLLMResponse) -> ClinicalRationale:
    """Map LLM response to a ClinicalRationale."""

    # Build primary factors from key_factors with highest magnitude
    sorted_factors = sorted(llm.key_factors, key=lambda f: abs(f.impact_magnitude), reverse=True)
    primary = [
        (kf.factor, abs(kf.impact_magnitude), f"{kf.value} ({kf.evidence_source})")
        for kf in sorted_factors[:5]
    ]
    secondary = [
        (kf.factor, abs(kf.impact_magnitude), f"{kf.value} ({kf.evidence_source})")
        for kf in sorted_factors[5:]
    ]

    # Feature contributions for SHAP-style chart
    feature_contributions = {
        kf.factor: kf.impact_magnitude * 40  # scale to eligibility-like range
        for kf in llm.key_factors
    }

    # Map recommendation
    rec_map = {
        "surgery": "surgery",
        "watch_wait": "watch_and_wait",
        "multidisciplinary": "uncertain",
    }
    recommended = rec_map.get(llm.recommendation, "uncertain")

    strength_map = {
        "low": "strong",
        "moderate": "moderate",
        "high": "weak",
    }
    strength = strength_map.get(llm.uncertainty_level, "moderate")

    return ClinicalRationale(
        primary_factors=primary,
        secondary_factors=secondary,
        surgery_benefits=[llm.surgery.narrative_fr],
        surgery_risks=llm.clinical_alerts[:3] if llm.recommendation != "surgery" else [],
        ww_benefits=[llm.watch_wait.narrative_fr],
        ww_risks=llm.clinical_alerts[:3] if llm.recommendation == "surgery" else [],
        recommended_scenario=recommended,
        recommendation_strength=strength,
        recommendation_text=llm.recommendation_rationale,
        feature_contributions=feature_contributions,
        clinical_alerts=llm.clinical_alerts,
    )


def _build_curve(dfs_2y: float, dfs_5y: float, scenario: str) -> SurvivalCurve:
    """Build a survival curve from 2y and 5y DFS anchors."""
    if scenario == "surgery":
        return SurvivalCurve(
            months_1=min(100.0, dfs_2y + 8),
            months_3=min(100.0, dfs_2y + 6),
            months_6=min(100.0, dfs_2y + 4),
            months_12=min(100.0, dfs_2y + 2),
            months_24=dfs_2y,
            months_36=(dfs_2y + dfs_5y) / 2,
            months_60=dfs_5y,
        )
    else:
        return SurvivalCurve(
            months_1=95.0,
            months_3=90.0,
            months_6=min(100.0, dfs_2y + 15),
            months_12=min(100.0, dfs_2y + 5),
            months_24=dfs_2y,
            months_36=(dfs_2y + dfs_5y) / 2,
            months_60=dfs_5y,
        )


# ---------------------------------------------------------------------------
# Main engine class
# ---------------------------------------------------------------------------

class BrainEngineV2:
    """LLM-Powered Clinical Decision Engine with heuristic fallback.

    Pipeline:
    1. Build patient context dict from PatientInput
    2. Call LLM (NVIDIA NIM)
    3. On success → map LLM response to DecisionResult
    4. On failure → fall back to CRFSimulator heuristics

    Usage:
        engine = BrainEngineV2()
        result = engine.run_decision(patient_input)
        print(result.llm_source)  # True if LLM was used
    """

    def __init__(self) -> None:
        self.simulator = CRFSimulator()

    def run_decision(self, patient_input: PatientInput) -> DecisionResult:
        """Run complete clinical decision pipeline."""

        # Always map to CRF format (needed for fallback and some UI data)
        crf_input = map_patient_input_to_crf(patient_input)

        # Try LLM path
        patient_context = _build_patient_context(patient_input)
        llm_response = call_medical_llm(patient_context)

        if llm_response is not None:
            logger.info("LLM response received — using LLM-powered analysis")
            surgery_outcome = _llm_to_surgery_outcome(llm_response)
            ww_outcome = _llm_to_ww_outcome(llm_response)
            rationale = _llm_to_rationale(llm_response)

            rec_map = {
                "surgery": "surgery",
                "watch_wait": "watch_and_wait",
                "multidisciplinary": "uncertain",
            }

            return DecisionResult(
                patient_input=patient_input,
                crf_input=crf_input,
                surgery_outcome=surgery_outcome,
                ww_outcome=ww_outcome,
                rationale=rationale,
                recommended_scenario=rec_map.get(llm_response.recommendation, "uncertain"),
                recommendation_strength="strong" if llm_response.uncertainty_level == "low" else "moderate" if llm_response.uncertainty_level == "moderate" else "weak",
                llm_source=True,
                llm_response=llm_response,
            )

        # Fallback to heuristic engine
        logger.info("LLM unavailable — falling back to heuristic engine")
        surgery_outcome, ww_outcome, rationale = self.simulator.simulate_outcomes(crf_input)

        return DecisionResult(
            patient_input=patient_input,
            crf_input=crf_input,
            surgery_outcome=surgery_outcome,
            ww_outcome=ww_outcome,
            rationale=rationale,
            recommended_scenario=rationale.recommended_scenario,
            recommendation_strength=rationale.recommendation_strength,
            llm_source=False,
            llm_response=None,
        )

    @staticmethod
    def get_survival_comparison_data(result: DecisionResult) -> Dict[str, Any]:
        """Extract data for Kaplan-Meier comparison visualization."""
        surgery_curve = result.surgery_outcome.survival_curve.to_dict()
        ww_curve = result.ww_outcome.survival_curve.to_dict()

        return {
            "months": list(surgery_curve.keys()),
            "surgery_dfs": list(surgery_curve.values()),
            "ww_dfs": list(ww_curve.values()),
            "surgery_label": f"Chirurgie (DFS 5a: {result.surgery_outcome.dfs_5_years:.0f}%)",
            "ww_label": f"Watch & Wait (DFS 5a: {result.ww_outcome.dfs_5_years:.0f}%)",
        }

    @staticmethod
    def get_risk_comparison_data(result: DecisionResult) -> Dict[str, Any]:
        """Extract comparative risk data for visualization."""
        return {
            "surgery": {
                "local_recurrence": result.surgery_outcome.local_recurrence_risk,
                "distant_metastasis": result.surgery_outcome.distant_metastasis_risk,
                "major_complication": result.surgery_outcome.major_complication_risk,
                "stoma": result.surgery_outcome.stoma_risk,
                "lars": result.surgery_outcome.lars_risk,
            },
            "watch_and_wait": {
                "local_recurrence": result.ww_outcome.local_recurrence_risk,
                "distant_metastasis": result.ww_outcome.distant_metastasis_risk,
                "regrowth": result.ww_outcome.regrowth_risk,
                "salvage_surgery": result.ww_outcome.salvage_surgery_risk,
            },
        }

    @staticmethod
    def get_explainability_data(result: DecisionResult) -> Dict[str, Any]:
        """Extract explainability data for SHAP-style visualization."""
        return {
            "feature_contributions": result.rationale.feature_contributions,
            "primary_factors": [
                {"name": var, "weight": weight, "description": desc}
                for var, weight, desc in result.rationale.primary_factors
            ],
            "secondary_factors": [
                {"name": var, "weight": weight, "description": desc}
                for var, weight, desc in result.rationale.secondary_factors
            ],
            "recommendation": {
                "scenario": result.recommended_scenario,
                "strength": result.recommendation_strength,
                "text": result.rationale.recommendation_text,
            },
            "alerts": result.rationale.clinical_alerts,
        }


# === Factory Function for Backward Compatibility ===

def create_brain_engine(version: str = "v2") -> BrainEngineV2:
    """Factory function to create brain engine instance."""
    normalized_version = version.strip().lower()
    if normalized_version in {"v2", "v1"}:
        return BrainEngineV2()
    raise ValueError(f"Unknown brain engine version: {version}")
