from predi_care.engine.mock_factory import (
    get_preset_scenario,
    generate_mock_cohort,
    generate_mock_patient,
    list_preset_scenarios,
)


def test_mock_patient_is_reproducible_with_seed() -> None:
    p1 = generate_mock_patient(seed=42)
    p2 = generate_mock_patient(seed=42)
    assert p1 == p2


def test_mock_cohort_size() -> None:
    cohort = generate_mock_cohort(size=8, base_seed=100)
    assert len(cohort) == 8


def test_mock_patient_has_required_keys() -> None:
    patient = generate_mock_patient(seed=1)
    required = {
        "ct_stage",
        "cn_stage",
        "cm_stage",
        "ace_baseline",
        "ace_current",
        "residual_tumor_ratio",
        "imaging_quality",
        "age",
        "performance_status",
    }
    assert required.issubset(patient.keys())


def test_preset_scenario_catalog_is_accessible() -> None:
    scenario_names = list_preset_scenarios()
    assert len(scenario_names) > 0

    scenario = get_preset_scenario(scenario_names[0])
    assert scenario is not None
    assert {"ct_stage", "cn_stage", "cm_stage"}.issubset(scenario.keys())


def test_get_preset_scenario_returns_none_for_unknown_name() -> None:
    assert get_preset_scenario("__unknown__") is None
