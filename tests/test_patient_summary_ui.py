from __future__ import annotations

from predi_care.engine.brain_engine import BrainEngineV4
from predi_care.engine.legacy_ui_adapter import to_legacy_decision_result
from predi_care.engine.patient_types import PatientInput
from predi_care.engine import llm_client
from predi_care.ui.comparative_ui import (
    _build_clinician_summary,
    _build_patient_scenario_cards,
    _resolve_patient_summary,
)


def _patient(**overrides: object) -> PatientInput:
    payload: PatientInput = PatientInput(
        ct_stage="cT3",
        cn_stage="cN1",
        cm_stage="cM0",
        ace_baseline=8.0,
        ace_current=3.0,
        residual_tumor_ratio=20.0,
        residual_size_cm=1.0,
        imaging_quality="Elevee",
        age=62,
        performance_status=1,
        mrtrg=2,
        crm_distance_mm=5.0,
    )
    payload.update(overrides)
    return payload


def test_ui_summary_replaces_generic_placeholder(monkeypatch) -> None:
    monkeypatch.setenv("LLM_FORCE_HEURISTIC", "1")
    patient = _patient(
        residual_tumor_ratio=58.0,
        residual_size_cm=2.8,
        mrtrg=4,
        ace_baseline=5.0,
        ace_current=7.2,
    )
    engine = BrainEngineV4()
    result_v4 = engine.run_decision(patient)
    result_v4.consensus.recommendation = "surgery"
    legacy = to_legacy_decision_result(patient, result_v4)
    legacy.llm_response = llm_client._validate_and_parse(  # type: ignore[attr-defined]
        {
            "surgery": {
                "recurrence_local_2y": 6.0,
                "recurrence_local_5y": 8.0,
                "recurrence_systemic_2y": 18.0,
                "survival_dfs_2y": 84.0,
                "survival_dfs_5y": 73.0,
                "complication_rate": 16.0,
                "lars_risk": 24.0,
                "colostomy_risk": 8.0,
                "r0_probability": 93.0,
                "narrative_fr": "text",
            },
            "watch_wait": {
                "regrowth_2y": 22.0,
                "regrowth_5y": 28.0,
                "salvage_surgery_success": 88.0,
                "systemic_relapse_if_regrowth": 20.0,
                "survival_dfs_2y": 82.0,
                "survival_dfs_5y": 71.0,
                "organ_preservation_2y": 77.0,
                "surveillance_burden": "moderate",
                "narrative_fr": "text",
            },
            "recommendation": "surgery",
            "recommendation_rationale": "text",
            "uncertainty_level": "moderate",
            "uncertainty_reason": "text",
            "clinical_alerts": [],
            "key_factors": [],
            "patient_friendly_summary": (
                "Cette synthese s'appuie sur un jumeau numerique clinique multi-agent. "
                "La decision therapeutique finale doit etre validee en reunion pluridisciplinaire."
            ),
        }
    )

    summary = _resolve_patient_summary(legacy)

    assert "jumeau numerique clinique multi-agent" not in summary.lower()
    assert "2.8 cm" in summary
    assert "operation" in summary.lower()
    assert "complication importante" not in summary.lower()
    assert "sans rechute" not in summary.lower()


def test_ui_summary_prefers_simple_deterministic_text(monkeypatch) -> None:
    monkeypatch.setenv("LLM_FORCE_HEURISTIC", "1")
    patient = _patient()
    engine = BrainEngineV4()
    legacy = to_legacy_decision_result(patient, engine.run_decision(patient))
    legacy.llm_response = llm_client._validate_and_parse(  # type: ignore[attr-defined]
        {
            "surgery": {
                "recurrence_local_2y": 6.0,
                "recurrence_local_5y": 8.0,
                "recurrence_systemic_2y": 18.0,
                "survival_dfs_2y": 84.0,
                "survival_dfs_5y": 73.0,
                "complication_rate": 16.0,
                "lars_risk": 24.0,
                "colostomy_risk": 8.0,
                "r0_probability": 93.0,
                "narrative_fr": "text",
            },
            "watch_wait": {
                "regrowth_2y": 22.0,
                "regrowth_5y": 28.0,
                "salvage_surgery_success": 88.0,
                "systemic_relapse_if_regrowth": 20.0,
                "survival_dfs_2y": 82.0,
                "survival_dfs_5y": 71.0,
                "organ_preservation_2y": 77.0,
                "surveillance_burden": "moderate",
                "narrative_fr": "text",
            },
            "recommendation": "surgery",
            "recommendation_rationale": "text",
            "uncertainty_level": "moderate",
            "uncertainty_reason": "text",
            "clinical_alerts": [],
            "key_factors": [],
            "patient_friendly_summary": (
                "Votre situation suggere une bonne reponse tumorale, avec une lesion residuelle faible "
                "et une balance benefice-risque a discuter autour d'une preservation d'organe."
            ),
        }
    )

    summary = _resolve_patient_summary(legacy)

    assert summary.startswith("Aujourd'hui")
    assert "lesion residuelle" not in summary.lower()
    assert "balance benefice-risque" not in summary.lower()


def test_clinician_summary_stays_technical(monkeypatch) -> None:
    monkeypatch.setenv("LLM_FORCE_HEURISTIC", "1")
    patient = _patient()
    engine = BrainEngineV4()
    legacy = to_legacy_decision_result(patient, engine.run_decision(patient))
    legacy.rationale.recommendation_text = (
        "Des contraintes protocolaires strictes sont activees et imposent une revue pluridisciplinaire. "
        "Contrefactuel cle: Si le TRG s'ameliorait a 2 ou moins, l'eligibilite a la surveillance active augmenterait."
    )
    legacy.rationale.primary_factors = [
        ("trg", 0.9, "Reponse tumorale insuffisante apres traitement neoadjuvant"),
        ("crm", 0.6, "Marge circonferentielle jugee menacante"),
    ]
    legacy.rationale.clinical_alerts = ["CRM menacant avec risque local accru."]

    summary = _build_clinician_summary(legacy)

    assert "Contrefactuel" in summary
    assert "Facteurs dominants" in summary
    assert "Alerte principale" in summary


def test_patient_cards_describe_both_options(monkeypatch) -> None:
    monkeypatch.setenv("LLM_FORCE_HEURISTIC", "1")
    patient = _patient(residual_tumor_ratio=16.0, residual_size_cm=0.8, mrtrg=2)
    engine = BrainEngineV4()
    legacy = to_legacy_decision_result(patient, engine.run_decision(patient))
    legacy.recommended_scenario = "uncertain"

    cards = _build_patient_scenario_cards(legacy)

    assert len(cards) == 2
    assert cards[0]["title"] == "Operation"
    assert cards[1]["title"] == "Surveillance rapprochee"
    assert any("complication importante" in point.lower() for point in cards[0]["points"])
    assert any("maladie peut revenir" in point.lower() for point in cards[1]["points"])
