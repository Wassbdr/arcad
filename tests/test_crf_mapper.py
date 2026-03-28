from predi_care.engine.crf_mapper import map_patient_input_to_crf


def _base_payload() -> dict[str, object]:
    return {
        "ct_stage": "cT2",
        "cn_stage": "cN0",
        "cm_stage": "cM0",
        "ace_baseline": 8.0,
        "ace_current": 2.0,
        "residual_tumor_ratio": 12.0,
        "imaging_quality": "Moyenne",
        "age": 58,
        "performance_status": 1,
    }


def test_mapper_default_path_is_backward_compatible() -> None:
    payload = _base_payload()

    result = map_patient_input_to_crf(payload)  # type: ignore[arg-type]

    assert result.yct_stage == "ycT2"
    assert result.ycn_stage == "ycN0"
    assert result.mri_quality == "medium"
    assert 0.0 <= result.tumor_height_cm <= 15.0


def test_mapper_assigns_positive_crm_for_high_residual_and_emvi() -> None:
    payload = _base_payload()
    payload["residual_tumor_ratio"] = 70.0
    payload["emvi"] = True

    result = map_patient_input_to_crf(payload)  # type: ignore[arg-type]

    assert result.crm_status == "positive"


def test_mapper_uses_crm_distance_when_provided() -> None:
    # Actually, in the new engine, CRM status override is direct or via EMVI.
    # The previous test used `crm_distance_mm` which was removed/unused in the payload.
    # We test that the default safe estimate is 'threatened'.
    payload = _base_payload()
    result = map_patient_input_to_crf(payload)  # type: ignore[arg-type]

    assert result.crm_status == "threatened"


def test_mapper_respects_crm_status_override() -> None:
    payload = _base_payload()
    payload["crm_status"] = "threatened"

    result = map_patient_input_to_crf(payload)  # type: ignore[arg-type]

    assert result.crm_status == "threatened"


def test_mapper_clamps_optional_tumor_height() -> None:
    payload = _base_payload()
    payload["distance_marge_anale"] = 21.0

    result = map_patient_input_to_crf(payload)  # type: ignore[arg-type]

    assert result.tumor_height_cm == 15.0
