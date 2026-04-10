"""Brain Engine V2 - High-Fidelity CRF-Based Decision Engine.

This module integrates the CRFSimulator with the existing PREDI-Care architecture,
providing backward compatibility while enabling high-fidelity simulations based on
GRECCAR data.

Version: 2.0
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Tuple

from predi_care.engine.brain_engine import PatientInput  # Legacy format
from predi_care.engine.crf_simulator import (
    CRFSimulator,
    CRFInput,
    ScenarioOutcome,
    ClinicalRationale,
)
from predi_care.engine.crf_mapper import map_patient_input_to_crf


@dataclass
class DecisionResult:
    """Complete decision output including both scenarios and rationale.

    This is the main output structure consumed by the UI.
    """

    # === Input Data ===
    patient_input: PatientInput  # Original input
    crf_input: CRFInput  # Mapped CRF format

    # === Scenario Outcomes ===
    surgery_outcome: ScenarioOutcome
    ww_outcome: ScenarioOutcome

    # === Rationale ===
    rationale: ClinicalRationale

    # === Recommendation Summary ===
    recommended_scenario: str  # "surgery", "watch_and_wait", "uncertain"
    recommendation_strength: str  # "strong", "moderate", "weak"

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
        }


class BrainEngineV2:
    """High-Fidelity Clinical Decision Engine based on GRECCAR CRF data.

    This engine replaces heuristic logic with probabilistic models derived from
    real-world GRECCAR studies (6, 9, 12).

    Key Features:
    - CRF-based input mapping (GRECCAR templates)
    - Bayesian-style outcome prediction
    - Survival curve generation (DFS)
    - SHAP-style explainability
    - Clinical rationale generation

    Usage:
        engine = BrainEngineV2()
        result = engine.run_decision(patient_input)
        print(result.rationale.get_formatted_rationale())
    """

    def __init__(self):
        """Initialize the engine with CRFSimulator."""
        self.simulator = CRFSimulator()

    def run_decision(self, patient_input: PatientInput) -> DecisionResult:
        """Run complete clinical decision pipeline.

        Args:
            patient_input: Legacy PatientInput format (from UI)

        Returns:
            DecisionResult with both scenarios and rationale
        """

        # === Step 1: Map legacy input to CRF format ===
        crf_input = map_patient_input_to_crf(patient_input)

        # === Step 2: Run CRF simulation ===
        surgery_outcome, ww_outcome, rationale = self.simulator.simulate_outcomes(crf_input)

        # === Step 3: Package results ===
        result = DecisionResult(
            patient_input=patient_input,
            crf_input=crf_input,
            surgery_outcome=surgery_outcome,
            ww_outcome=ww_outcome,
            rationale=rationale,
            recommended_scenario=rationale.recommended_scenario,
            recommendation_strength=rationale.recommendation_strength,
        )

        return result

    @staticmethod
    def get_survival_comparison_data(result: DecisionResult) -> Dict[str, Any]:
        """Extract data for Kaplan-Meier comparison visualization.

        Returns:
            Dict with survival curves for both scenarios formatted for Plotly
        """
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
        """Extract comparative risk data for visualization.

        Returns:
            Dict with risks for both scenarios
        """
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
        """Extract explainability data for SHAP-style visualization.

        Returns:
            Dict with feature contributions and factor weights
        """
        return {
            "feature_contributions": result.rationale.feature_contributions,
            "primary_factors": [
                {
                    "name": var,
                    "weight": weight,
                    "description": desc,
                }
                for var, weight, desc in result.rationale.primary_factors
            ],
            "secondary_factors": [
                {
                    "name": var,
                    "weight": weight,
                    "description": desc,
                }
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
    """Factory function to create appropriate brain engine version.

    Args:
        version: "v2" (CRF-based, default) or "v1" (legacy heuristic)

    Returns:
        BrainEngine instance
    """
    if version == "v2":
        return BrainEngineV2()
    elif version == "v1":
        # Import legacy engine if needed
        from predi_care.engine.brain_engine import BrainEngine
        return BrainEngine()  # type: ignore
    else:
        raise ValueError(f"Unknown brain engine version: {version}")
