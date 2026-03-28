import json
from unittest.mock import patch, MagicMock

import pytest

from predi_care.engine.llm_client import (
    call_medical_llm,
    MedicalLLMResponse,
    _validate_and_parse,
)


@pytest.fixture
def mock_patient_data():
    return {
        "clinical": {
            "cT": 3,
            "cN": 1,
            "cM": 0,
            "age": 60,
            "ecog": 0,
            "sphincter_preserved": True,
            "distance_marge_anale": 8.0,
        },
        "response": {
            "residual_size_cm": 1.5,
            "trg_rodel": 2,
            "clinical_response_tr": "partial",
            "delay_weeks_post_rct": 8,
            "protocol_neoadjuvant": "RCT standard",
        },
        "imaging": {
            "crm_mm": 5.0,
            "emvi": False,
            "mrtrg": 3,
            "mri_quality": "good",
        },
        "biology": {
            "ace_baseline": 15.0,
            "ace_current": 3.0,
            "hemoglobin": 13.5,
            "albumin": 40.0,
            "nlr_ratio": 2.5,
            "msi_status": "MSS/MSI-L",
        },
        "comorbidities": {
            "asa_score": 1,
            "smoking": False,
            "diabetes": False,
            "bmi": 25,
        },
    }


def test_validate_and_parse_valid_json():
    """Test parsing a valid LLM JSON response."""
    raw_json = {
        "surgery": {
            "recurrence_local_2y": 5.0,
            "recurrence_local_5y": 7.5,
            "recurrence_systemic_2y": 15.0,
            "survival_dfs_2y": 80.0,
            "survival_dfs_5y": 75.0,
            "complication_rate": 20.0,
            "lars_risk": 25.0,
            "colostomy_risk": 5.0,
            "r0_probability": 95.0,
            "narrative_fr": "Chirurgie indiquee avec bon pronostic."
        },
        "watch_wait": {
            "regrowth_2y": 25.0,
            "regrowth_5y": 30.0,
            "salvage_surgery_success": 90.0,
            "systemic_relapse_if_regrowth": 20.0,
            "survival_dfs_2y": 85.0,
            "survival_dfs_5y": 80.0,
            "organ_preservation_2y": 75.0,
            "surveillance_burden": "moderate",
            "narrative_fr": "Surveillance possible mais risque de repousse non negligeable."
        },
        "recommendation": "surgery",
        "recommendation_rationale": "Le patient est un bon candidat pour la chirurgie.",
        "uncertainty_level": "low",
        "uncertainty_reason": "",
        "clinical_alerts": ["Attention a la denutrition."],
        "key_factors": [
            {
                "factor": "mrTRG",
                "value": "3",
                "direction": "neutral",
                "impact_magnitude": 0.2,
                "evidence_source": "GRECCAR"
            }
        ],
        "patient_friendly_summary": "Votre tumeur a bien repondu au traitement prealable. L'operation est l'option la plus sure."
    }

    response: MedicalLLMResponse = _validate_and_parse(raw_json)
    assert response.surgery.recurrence_local_2y == 5.0
    assert response.watch_wait.organ_preservation_2y == 75.0
    assert response.recommendation == "surgery"
    assert len(response.key_factors) == 1
    assert response.key_factors[0].factor == "mrTRG"
    assert response.patient_friendly_summary.startswith("Votre tumeur")


def test_validate_and_parse_clamping():
    """Test that probablities limits and magnitude limits are clamped."""
    raw_json = {
        "surgery": {
            "recurrence_local_2y": -5.0,        # Should clamp to 0
            "recurrence_local_5y": 150.0,       # Should clamp to 100
            "recurrence_systemic_2y": 0.0,
            "survival_dfs_2y": 0.0,
            "survival_dfs_5y": 0.0,
            "complication_rate": 0.0,
            "lars_risk": 0.0,
            "colostomy_risk": 0.0,
            "r0_probability": 0.0,
        },
        "watch_wait": {
            "regrowth_2y": 0.0,
            "regrowth_5y": 0.0,
            "salvage_surgery_success": 0.0,
            "systemic_relapse_if_regrowth": 0.0,
            "survival_dfs_2y": 0.0,
            "survival_dfs_5y": 0.0,
            "organ_preservation_2y": 0.0,
            "surveillance_burden": "low",
        },
        "recommendation": "watch_wait",
        "key_factors": [
            {
                "factor": "test",
                "value": "test",
                "direction": "neutral",
                "impact_magnitude": 2.5,  # Should clamp to 1.0
                "evidence_source": "test"
            }
        ],
    }
    
    response = _validate_and_parse(raw_json)
    assert response.surgery.recurrence_local_2y == 0.0
    assert response.surgery.recurrence_local_5y == 100.0
    assert response.key_factors[0].impact_magnitude == 1.0


@patch("predi_care.engine.llm_client._get_api_key", return_value=None)
def test_call_llm_no_api_key(mock_get_key, mock_patient_data):
    """Test that None is returned when API key is missing, triggering fallback in engine."""
    result = call_medical_llm(mock_patient_data)
    assert result is None
