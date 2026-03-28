from __future__ import annotations

from predi_care.engine.brain_engine import BrainEngineV4
from predi_care.engine.patient_types import PatientInput


def _base_patient(**overrides: object) -> PatientInput:
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


def test_cm1_forces_multidisciplinary(monkeypatch) -> None:
    monkeypatch.setenv("LLM_FORCE_HEURISTIC", "1")
    engine = BrainEngineV4()
    result = engine.run_decision(_base_patient(cm_stage="cM1"))
    assert result.consensus.recommendation == "multidisciplinary"


def test_ecog4_forces_multidisciplinary(monkeypatch) -> None:
    monkeypatch.setenv("LLM_FORCE_HEURISTIC", "1")
    engine = BrainEngineV4()
    result = engine.run_decision(_base_patient(performance_status=4))
    assert result.consensus.recommendation == "multidisciplinary"


def test_watch_wait_forbidden_when_residual_gt_2(monkeypatch) -> None:
    monkeypatch.setenv("LLM_FORCE_HEURISTIC", "1")
    engine = BrainEngineV4()
    result = engine.run_decision(_base_patient(residual_size_cm=2.6, residual_tumor_ratio=52.0, mrtrg=2))
    assert result.consensus.recommendation != "watch_wait"


def test_watch_wait_forbidden_when_trg_gt_2(monkeypatch) -> None:
    monkeypatch.setenv("LLM_FORCE_HEURISTIC", "1")
    engine = BrainEngineV4()
    result = engine.run_decision(_base_patient(mrtrg=4, residual_size_cm=1.0))
    assert result.consensus.recommendation != "watch_wait"


def test_probabilities_are_bounded(monkeypatch) -> None:
    monkeypatch.setenv("LLM_FORCE_HEURISTIC", "1")
    engine = BrainEngineV4()
    result = engine.run_decision(_base_patient())

    values = [
        result.surgery.survival_2y,
        result.surgery.survival_5y,
        result.surgery.local_recurrence_2y,
        result.surgery.local_recurrence_5y,
        result.surgery.major_complication,
        result.watch_wait.survival_2y,
        result.watch_wait.survival_5y,
        result.watch_wait.local_recurrence_2y,
        result.watch_wait.local_recurrence_5y,
        result.watch_wait.major_complication,
    ]
    assert all(0.0 <= value <= 100.0 for value in values)


def test_survival_curves_are_monotone(monkeypatch) -> None:
    monkeypatch.setenv("LLM_FORCE_HEURISTIC", "1")
    engine = BrainEngineV4()
    result = engine.run_decision(_base_patient())

    for curve in (result.surgery.survival_curve, result.watch_wait.survival_curve):
        points = [curve[month] for month in sorted(curve.keys())]
        assert all(next_value <= value for value, next_value in zip(points[:-1], points[1:]))

