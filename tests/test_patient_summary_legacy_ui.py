from __future__ import annotations

from predi_care.engine.brain_engine import BrainEngineV4
from predi_care.engine.legacy_ui_adapter import _build_patient_friendly_summary
from predi_care.engine.patient_types import PatientInput


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


def test_patient_summary_watch_wait_is_contextualized(monkeypatch) -> None:
    monkeypatch.setenv("LLM_FORCE_HEURISTIC", "1")
    engine = BrainEngineV4()
    result = engine.run_decision(
        _patient(
            residual_tumor_ratio=4.0,
            residual_size_cm=0.4,
            mrtrg=1,
            ace_baseline=8.0,
            ace_current=2.0,
        )
    )
    result.consensus.recommendation = "watch_wait"

    summary = _build_patient_friendly_summary(result)

    assert "surveillance active" in summary.lower()
    assert "repousse locale" in summary.lower()
    assert "0.4 cm" in summary
    assert "jumeau numerique clinique multi-agent" not in summary.lower()


def test_patient_summary_surgery_explains_benefit_and_risk(monkeypatch) -> None:
    monkeypatch.setenv("LLM_FORCE_HEURISTIC", "1")
    engine = BrainEngineV4()
    result = engine.run_decision(
        _patient(
            residual_tumor_ratio=58.0,
            residual_size_cm=2.8,
            mrtrg=4,
            ace_baseline=5.0,
            ace_current=7.2,
        )
    )
    result.consensus.recommendation = "surgery"

    summary = _build_patient_friendly_summary(result)

    assert "chirurgie" in summary.lower()
    assert "complication importante" in summary.lower()
    assert "2.8 cm" in summary
    assert "chance de rester sans rechute" in summary.lower()
