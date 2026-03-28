from pathlib import Path

import pytest

from predi_care.data.loader import load_patients_from_csv, load_patients_from_csv_result


def _write_csv(tmp_path: Path, content: str) -> Path:
    csv_path = tmp_path / "cohort.csv"
    csv_path.write_text(content, encoding="utf-8")
    return csv_path


def test_demo_csv_loads_without_errors() -> None:
    root = Path(__file__).resolve().parent.parent
    csv_path = root / "data" / "cohorts" / "demo.csv"

    result = load_patients_from_csv_result(csv_path)

    assert len(result.errors) == 0
    assert len(result.warnings) == 0
    assert len(result.patients) == 6


def test_wrapper_returns_patients_list_when_valid() -> None:
    root = Path(__file__).resolve().parent.parent
    csv_path = root / "data" / "cohorts" / "demo.csv"

    patients = load_patients_from_csv(csv_path)

    assert len(patients) == 6
    assert "input" in patients[0]


def test_loader_applies_defaults_when_optional_columns_missing(tmp_path: Path) -> None:
    csv_path = _write_csv(
        tmp_path=tmp_path,
        content=(
            "patient_id,ct_stage,cn_stage,cm_stage\n"
            "P001,cT2,cN0,cM0\n"
        ),
    )

    result = load_patients_from_csv_result(csv_path)

    assert len(result.errors) == 0
    assert len(result.patients) == 1

    payload = result.patients[0]["input"]
    assert payload["ace_baseline"] == 8.5
    assert payload["ace_current"] == 2.1
    assert payload["residual_tumor_ratio"] == 15.0
    assert payload["imaging_quality"] == "Moyenne"
    assert payload["age"] == 62
    assert payload["performance_status"] == 0

    assert any(issue.field == "__columns__" for issue in result.warnings)


def test_loader_reports_missing_required_columns(tmp_path: Path) -> None:
    csv_path = _write_csv(
        tmp_path=tmp_path,
        content=(
            "patient_id,ct_stage,cn_stage,ace_baseline,ace_current,residual_tumor_ratio,"
            "imaging_quality,age,performance_status\n"
            "P001,cT2,cN0,5.0,2.0,10.0,Elevee,55,0\n"
        ),
    )

    result = load_patients_from_csv_result(csv_path)

    assert len(result.errors) == 1
    assert result.errors[0].field == "__columns__"


def test_loader_clamps_out_of_range_values_with_warnings(tmp_path: Path) -> None:
    csv_path = _write_csv(
        tmp_path=tmp_path,
        content=(
            "patient_id,ct_stage,cn_stage,cm_stage,ace_baseline,ace_current,residual_tumor_ratio,"
            "imaging_quality,age,performance_status\n"
            "P001,cT2,cN0,cM0,5.0,-4.0,120.0,Elevee,150,9\n"
        ),
    )

    result = load_patients_from_csv_result(csv_path)

    assert len(result.errors) == 0
    assert len(result.patients) == 1

    payload = result.patients[0]["input"]
    assert payload["ace_current"] == 0.0
    assert payload["residual_tumor_ratio"] == 100.0
    assert payload["age"] == 100
    assert payload["performance_status"] == 4

    warned_fields = {issue.field for issue in result.warnings}
    assert {"ace_current", "residual_tumor_ratio", "age", "performance_status"}.issubset(warned_fields)


def test_loader_renames_duplicate_patient_ids(tmp_path: Path) -> None:
    csv_path = _write_csv(
        tmp_path=tmp_path,
        content=(
            "patient_id,ct_stage,cn_stage,cm_stage,ace_baseline,ace_current,residual_tumor_ratio,"
            "imaging_quality,age,performance_status\n"
            "DUP,cT2,cN0,cM0,5.0,2.0,10.0,Elevee,55,0\n"
            "DUP,cT3,cN1,cM0,6.0,2.5,20.0,Moyenne,60,1\n"
        ),
    )

    result = load_patients_from_csv_result(csv_path)

    assert len(result.errors) == 0
    assert len(result.patients) == 2
    assert result.patients[0]["patient_id"] == "DUP"
    assert result.patients[1]["patient_id"] == "DUP_2"
    assert any(issue.field == "patient_id" for issue in result.warnings)


def test_loader_skips_invalid_rows_and_keeps_valid_rows(tmp_path: Path) -> None:
    csv_path = _write_csv(
        tmp_path=tmp_path,
        content=(
            "patient_id,ct_stage,cn_stage,cm_stage,ace_baseline,ace_current,residual_tumor_ratio,"
            "imaging_quality,age,performance_status\n"
            "BAD,cT9,cN0,cM0,5.0,2.0,10.0,Elevee,55,0\n"
            "OK,cT2,cN0,cM0,5.0,2.0,10.0,Elevee,55,0\n"
        ),
    )

    result = load_patients_from_csv_result(csv_path)

    assert len(result.patients) == 1
    assert result.patients[0]["patient_id"] == "OK"
    assert any(issue.field == "ct_stage" for issue in result.errors)


def test_wrapper_raises_when_blocking_errors_exist(tmp_path: Path) -> None:
    csv_path = _write_csv(
        tmp_path=tmp_path,
        content=(
            "patient_id,ct_stage,cn_stage,cm_stage,ace_baseline,ace_current,residual_tumor_ratio,"
            "imaging_quality,age,performance_status\n"
            "BAD,cT9,cN0,cM0,5.0,2.0,10.0,Elevee,55,0\n"
        ),
    )

    with pytest.raises(ValueError, match="Invalid CSV input"):
        load_patients_from_csv(csv_path)
