from predi_care.engine.brain_engine import PatientInput, render_decision_lines, run_multimodal_pipeline


def test_pipeline_returns_expected_sections() -> None:
    payload: PatientInput = {
        "ct_stage": "cT3",
        "cn_stage": "cN1",
        "cm_stage": "cM0",
        "ace_baseline": 12.0,
        "ace_current": 4.2,
        "residual_tumor_ratio": 25.0,
        "imaging_quality": "Elevee",
        "age": 59,
        "performance_status": 1,
    }

    result = run_multimodal_pipeline(payload)
    assert "radiology" in result
    assert "biology" in result
    assert "coordinator" in result


def test_pipeline_scores_are_bounded() -> None:
    payload: PatientInput = {
        "ct_stage": "cT4",
        "cn_stage": "cN2",
        "cm_stage": "cM0",
        "ace_baseline": 22.0,
        "ace_current": 14.0,
        "residual_tumor_ratio": 62.0,
        "imaging_quality": "Moyenne",
        "age": 71,
        "performance_status": 3,
    }

    result = run_multimodal_pipeline(payload)
    coordinator = result["coordinator"]
    assert 0.0 <= coordinator["recurrence_probability"] <= 1.0
    assert 0.0 <= coordinator["scenario_surgery"]["risk"] <= 1.0
    assert 0.0 <= coordinator["scenario_watch_wait"]["risk"] <= 1.0


def test_recommendation_label_is_valid() -> None:
    payload: PatientInput = {
        "ct_stage": "cT2",
        "cn_stage": "cN0",
        "cm_stage": "cM0",
        "ace_baseline": 6.0,
        "ace_current": 2.5,
        "residual_tumor_ratio": 10.0,
        "imaging_quality": "Elevee",
        "age": 48,
        "performance_status": 0,
    }

    recommendation = run_multimodal_pipeline(payload)["coordinator"]["recommendation"]
    assert recommendation in {"Watch and Wait", "Chirurgie Radicale"}


def test_cm1_forces_radical_strategy() -> None:
    payload: PatientInput = {
        "ct_stage": "cT2",
        "cn_stage": "cN0",
        "cm_stage": "cM1",
        "ace_baseline": 4.0,
        "ace_current": 3.0,
        "residual_tumor_ratio": 12.0,
        "imaging_quality": "Elevee",
        "age": 50,
        "performance_status": 1,
    }
    result = run_multimodal_pipeline(payload)["coordinator"]
    assert result["recommendation"] == "Chirurgie Radicale"
    assert result["rule_flags"]["tnm_high_alert"] is True


def test_conflict_and_uncertainty_are_reported() -> None:
    payload: PatientInput = {
        "ct_stage": "cT1",
        "cn_stage": "cN0",
        "cm_stage": "cM0",
        "ace_baseline": 11.0,
        "ace_current": 10.0,
        "residual_tumor_ratio": 8.0,
        "imaging_quality": "Moyenne",
        "age": 58,
        "performance_status": 1,
    }
    result = run_multimodal_pipeline(payload)["coordinator"]
    assert result["conflict_detected"] is True
    assert len(result["conflict_reasons"]) > 0
    assert result["uncertainty_level"] in {"Moyenne", "Elevee"}
    assert result["rule_flags"]["ace_alert"] is True


def test_decision_lines_include_governance_fields() -> None:
    payload: PatientInput = {
        "ct_stage": "cT3",
        "cn_stage": "cN1",
        "cm_stage": "cM0",
        "ace_baseline": 12.0,
        "ace_current": 6.2,
        "residual_tumor_ratio": 32.0,
        "imaging_quality": "Elevee",
        "age": 63,
        "performance_status": 2,
    }
    pack = run_multimodal_pipeline(payload)
    lines = render_decision_lines(pack)
    joined = " | ".join(lines)
    assert "Niveau d'incertitude" in joined
    assert "Conflit detecte" in joined
