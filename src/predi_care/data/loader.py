"""CSV data loader for patient cohorts."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

from predi_care.engine.patient_types import PatientInput


REQUIRED_COLUMNS = [
    "ct_stage",
    "cn_stage",
    "cm_stage",
]

OPTIONAL_DEFAULT_VALUES = {
    "ace_baseline": 8.5,
    "ace_current": 2.1,
    "residual_tumor_ratio": 15.0,
    "imaging_quality": "Moyenne",
    "age": 62,
    "performance_status": 0,
}

EXPECTED_COLUMNS = [
    "ct_stage",
    "cn_stage",
    "cm_stage",
    "ace_baseline",
    "ace_current",
    "residual_tumor_ratio",
    "imaging_quality",
    "age",
    "performance_status",
]

CT_STAGE_VALUES = {"cT1", "cT2", "cT3", "cT4"}
CN_STAGE_VALUES = {"cN0", "cN1", "cN2"}
CM_STAGE_VALUES = {"cM0", "cM1"}
IMAGING_QUALITY_VALUES = {"Elevee", "Moyenne", "Basse"}


@dataclass(frozen=True)
class ValidationIssue:
    """Validation issue raised during cohort loading."""

    row_number: int
    field: str
    value: str
    message: str


@dataclass
class LoadResult:
    """Structured output for cohort ingestion."""

    patients: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[ValidationIssue] = field(default_factory=list)
    errors: List[ValidationIssue] = field(default_factory=list)


def load_patients_from_csv(filepath: Path) -> List[Dict[str, Any]]:
    """Load patient data from a CSV file.

    Backward-compatible wrapper: returns valid patients.
    Raises ValueError when at least one blocking error is found.

    Required CSV columns:
    - ct_stage: "cT1", "cT2", "cT3", "cT4"
    - cn_stage: "cN0", "cN1", "cN2"
    - cm_stage: "cM0", "cM1"

    Optional columns (defaults applied if missing):
    - patient_id: generated if absent
    - ace_baseline: default 8.5
    - ace_current: default 2.1
    - residual_tumor_ratio: default 15.0
    - imaging_quality: default "Moyenne"
    - age: default 62
    - performance_status: default 0

    Returns:
        List of dicts with patient_id and PatientInput fields.
    """
    result = load_patients_from_csv_result(filepath)
    if result.errors:
        first_error = result.errors[0]
        raise ValueError(
            "Invalid CSV input: "
            f"{len(result.errors)} error(s). "
            f"First error at row {first_error.row_number}, field '{first_error.field}': {first_error.message}"
        )

    return result.patients


def load_patients_from_csv_result(filepath: Path) -> LoadResult:
    """Load patient data from CSV with structured warnings and errors."""
    result = LoadResult()

    try:
        rows, fieldnames = _read_rows_with_fallback_encodings(filepath)
    except ValueError as exc:
        result.errors.append(
            ValidationIssue(
                row_number=0,
                field="__file__",
                value=str(filepath),
                message=str(exc),
            )
        )
        return result

    missing_columns = [column for column in REQUIRED_COLUMNS if column not in fieldnames]
    if missing_columns:
        result.errors.append(
            ValidationIssue(
                row_number=1,
                field="__columns__",
                value=", ".join(missing_columns),
                message=(
                    "Missing required columns. "
                    f"Expected at minimum: {', '.join(REQUIRED_COLUMNS)}."
                ),
            )
        )
        return result

    missing_optional = [
        column for column in EXPECTED_COLUMNS if column not in fieldnames and column not in REQUIRED_COLUMNS
    ]
    if missing_optional:
        result.warnings.append(
            ValidationIssue(
                row_number=1,
                field="__columns__",
                value=", ".join(missing_optional),
                message="Optional columns missing. Defaults will be used.",
            )
        )

    seen_patient_ids: Dict[str, int] = {}
    for row_number, row in enumerate(rows, start=2):
        patient_record = _parse_patient_row(
            row=row,
            row_number=row_number,
            patient_index=len(result.patients) + 1,
            warnings=result.warnings,
            errors=result.errors,
        )
        if patient_record is None:
            continue

        original_id = str(patient_record["patient_id"])
        unique_id = _make_unique_patient_id(original_id, seen_patient_ids)
        if unique_id != original_id:
            result.warnings.append(
                ValidationIssue(
                    row_number=row_number,
                    field="patient_id",
                    value=original_id,
                    message=f"Duplicate patient_id detected. Renamed to '{unique_id}'.",
                )
            )
            patient_record["patient_id"] = unique_id

        result.patients.append(patient_record)

    if not result.patients and not result.errors:
        result.errors.append(
            ValidationIssue(
                row_number=1,
                field="__file__",
                value=str(filepath),
                message="CSV file contains no patient rows.",
            )
        )

    return result


def _read_rows_with_fallback_encodings(filepath: Path) -> tuple[List[Dict[str, str]], List[str]]:
    """Read a CSV file with graceful encoding fallback."""
    encodings = ["utf-8-sig", "utf-8", "latin-1"]
    for encoding in encodings:
        try:
            with open(filepath, encoding=encoding, newline="") as handle:
                reader = csv.DictReader(handle)
                rows = list(reader)
                return rows, list(reader.fieldnames or [])
        except UnicodeDecodeError:
            continue

    raise ValueError(
        "Unable to decode CSV with supported encodings (utf-8-sig, utf-8, latin-1)."
    )


def _parse_patient_row(
    row: Dict[str, str],
    row_number: int,
    patient_index: int,
    warnings: List[ValidationIssue],
    errors: List[ValidationIssue],
) -> Dict[str, Any] | None:
    """Parse and validate one row into a patient record."""
    patient_id = (row.get("patient_id") or "").strip() or f"P{patient_index:03d}"

    ct_stage = _parse_choice(row, row_number, "ct_stage", CT_STAGE_VALUES, errors)
    cn_stage = _parse_choice(row, row_number, "cn_stage", CN_STAGE_VALUES, errors)
    cm_stage = _parse_choice(row, row_number, "cm_stage", CM_STAGE_VALUES, errors)
    imaging_quality = _parse_optional_imaging_quality(
        row=row,
        row_number=row_number,
        warnings=warnings,
        errors=errors,
    )

    ace_baseline = _parse_optional_float(
        row=row,
        row_number=row_number,
        field_name="ace_baseline",
        default_value=float(OPTIONAL_DEFAULT_VALUES["ace_baseline"]),
        warnings=warnings,
        errors=errors,
    )
    ace_current = _parse_optional_float(
        row=row,
        row_number=row_number,
        field_name="ace_current",
        default_value=float(OPTIONAL_DEFAULT_VALUES["ace_current"]),
        warnings=warnings,
        errors=errors,
    )
    residual_tumor_ratio = _parse_optional_float(
        row=row,
        row_number=row_number,
        field_name="residual_tumor_ratio",
        default_value=float(OPTIONAL_DEFAULT_VALUES["residual_tumor_ratio"]),
        warnings=warnings,
        errors=errors,
    )
    age = _parse_optional_int(
        row=row,
        row_number=row_number,
        field_name="age",
        default_value=int(OPTIONAL_DEFAULT_VALUES["age"]),
        warnings=warnings,
        errors=errors,
    )
    performance_status = _parse_optional_int(
        row=row,
        row_number=row_number,
        field_name="performance_status",
        default_value=int(OPTIONAL_DEFAULT_VALUES["performance_status"]),
        warnings=warnings,
        errors=errors,
    )

    if (
        ct_stage is None
        or cn_stage is None
        or cm_stage is None
        or imaging_quality is None
        or ace_baseline is None
        or ace_current is None
        or residual_tumor_ratio is None
        or age is None
        or performance_status is None
    ):
        return None

    ace_baseline = _clamp_float("ace_baseline", ace_baseline, 0.0, 150.0, row_number, warnings)
    ace_current = _clamp_float("ace_current", ace_current, 0.0, 150.0, row_number, warnings)
    residual_tumor_ratio = _clamp_float(
        "residual_tumor_ratio",
        residual_tumor_ratio,
        0.0,
        100.0,
        row_number,
        warnings,
    )
    age = _clamp_int("age", age, 18, 100, row_number, warnings)
    performance_status = _clamp_int(
        "performance_status",
        performance_status,
        0,
        4,
        row_number,
        warnings,
    )

    patient_payload: Dict[str, Any] = {
        "patient_id": patient_id,
        "input": PatientInput(
            ct_stage=ct_stage,
            cn_stage=cn_stage,
            cm_stage=cm_stage,
            ace_baseline=ace_baseline,
            ace_current=ace_current,
            residual_tumor_ratio=residual_tumor_ratio,
            imaging_quality=imaging_quality,
            age=age,
            performance_status=performance_status,
        ),
    }
    return patient_payload


def _parse_choice(
    row: Dict[str, str],
    row_number: int,
    field_name: str,
    allowed_values: set[str],
    errors: List[ValidationIssue],
) -> str | None:
    """Parse a string field constrained to an enum."""
    raw_value = (row.get(field_name) or "").strip()
    if not raw_value:
        errors.append(
            ValidationIssue(
                row_number=row_number,
                field=field_name,
                value="",
                message="Missing required value.",
            )
        )
        return None

    lookup = {value.lower(): value for value in allowed_values}
    normalized = lookup.get(raw_value.replace(" ", "").lower())
    if normalized is not None:
        return normalized

    errors.append(
        ValidationIssue(
            row_number=row_number,
            field=field_name,
            value=raw_value,
            message=f"Invalid value. Expected one of: {', '.join(sorted(allowed_values))}.",
        )
    )
    return None


def _parse_imaging_quality(
    row: Dict[str, str],
    row_number: int,
    errors: List[ValidationIssue],
) -> str | None:
    """Parse imaging quality with accent-insensitive normalization."""
    raw_value = (row.get("imaging_quality") or "").strip()
    if not raw_value:
        errors.append(
            ValidationIssue(
                row_number=row_number,
                field="imaging_quality",
                value="",
                message="Missing required value.",
            )
        )
        return None

    normalized = raw_value.lower()
    normalized = normalized.replace("é", "e").replace("è", "e").replace("ê", "e")
    mapping = {
        "elevee": "Elevee",
        "moyenne": "Moyenne",
        "basse": "Basse",
    }
    resolved = mapping.get(normalized)
    if resolved is not None:
        return resolved

    errors.append(
        ValidationIssue(
            row_number=row_number,
            field="imaging_quality",
            value=raw_value,
            message=(
                "Invalid value. Expected one of: "
                f"{', '.join(sorted(IMAGING_QUALITY_VALUES))}."
            ),
        )
    )
    return None


def _parse_optional_imaging_quality(
    row: Dict[str, str],
    row_number: int,
    warnings: List[ValidationIssue],
    errors: List[ValidationIssue],
) -> str | None:
    """Parse optional imaging quality field with default fallback."""
    raw_value = (row.get("imaging_quality") or "").strip()
    if not raw_value:
        warnings.append(
            ValidationIssue(
                row_number=row_number,
                field="imaging_quality",
                value="",
                message=f"Missing value. Default '{OPTIONAL_DEFAULT_VALUES['imaging_quality']}' applied.",
            )
        )
        return str(OPTIONAL_DEFAULT_VALUES["imaging_quality"])

    return _parse_imaging_quality(row, row_number, errors)


def _parse_optional_float(
    row: Dict[str, str],
    row_number: int,
    field_name: str,
    default_value: float,
    warnings: List[ValidationIssue],
    errors: List[ValidationIssue],
) -> float | None:
    """Parse optional float field with default fallback."""
    raw_value = (row.get(field_name) or "").strip()
    if not raw_value:
        warnings.append(
            ValidationIssue(
                row_number=row_number,
                field=field_name,
                value="",
                message=f"Missing value. Default '{default_value}' applied.",
            )
        )
        return default_value

    return _parse_float(row, row_number, field_name, errors)


def _parse_optional_int(
    row: Dict[str, str],
    row_number: int,
    field_name: str,
    default_value: int,
    warnings: List[ValidationIssue],
    errors: List[ValidationIssue],
) -> int | None:
    """Parse optional integer field with default fallback."""
    raw_value = (row.get(field_name) or "").strip()
    if not raw_value:
        warnings.append(
            ValidationIssue(
                row_number=row_number,
                field=field_name,
                value="",
                message=f"Missing value. Default '{default_value}' applied.",
            )
        )
        return default_value

    return _parse_int(row, row_number, field_name, errors)


def _parse_float(
    row: Dict[str, str],
    row_number: int,
    field_name: str,
    errors: List[ValidationIssue],
) -> float | None:
    """Parse a required float field."""
    raw_value = (row.get(field_name) or "").strip()
    if not raw_value:
        errors.append(
            ValidationIssue(
                row_number=row_number,
                field=field_name,
                value="",
                message="Missing required numeric value.",
            )
        )
        return None

    try:
        return float(raw_value)
    except ValueError:
        errors.append(
            ValidationIssue(
                row_number=row_number,
                field=field_name,
                value=raw_value,
                message="Invalid numeric value.",
            )
        )
        return None


def _parse_int(
    row: Dict[str, str],
    row_number: int,
    field_name: str,
    errors: List[ValidationIssue],
) -> int | None:
    """Parse a required integer field."""
    raw_value = (row.get(field_name) or "").strip()
    if not raw_value:
        errors.append(
            ValidationIssue(
                row_number=row_number,
                field=field_name,
                value="",
                message="Missing required integer value.",
            )
        )
        return None

    try:
        return int(float(raw_value))
    except ValueError:
        errors.append(
            ValidationIssue(
                row_number=row_number,
                field=field_name,
                value=raw_value,
                message="Invalid integer value.",
            )
        )
        return None


def _clamp_float(
    field_name: str,
    value: float,
    min_value: float,
    max_value: float,
    row_number: int,
    warnings: List[ValidationIssue],
) -> float:
    """Clamp float values to accepted ranges while reporting warnings."""
    if value < min_value:
        warnings.append(
            ValidationIssue(
                row_number=row_number,
                field=field_name,
                value=str(value),
                message=f"Value below minimum {min_value}. Clamped.",
            )
        )
        return min_value

    if value > max_value:
        warnings.append(
            ValidationIssue(
                row_number=row_number,
                field=field_name,
                value=str(value),
                message=f"Value above maximum {max_value}. Clamped.",
            )
        )
        return max_value

    return value


def _clamp_int(
    field_name: str,
    value: int,
    min_value: int,
    max_value: int,
    row_number: int,
    warnings: List[ValidationIssue],
) -> int:
    """Clamp integer values to accepted ranges while reporting warnings."""
    if value < min_value:
        warnings.append(
            ValidationIssue(
                row_number=row_number,
                field=field_name,
                value=str(value),
                message=f"Value below minimum {min_value}. Clamped.",
            )
        )
        return min_value

    if value > max_value:
        warnings.append(
            ValidationIssue(
                row_number=row_number,
                field=field_name,
                value=str(value),
                message=f"Value above maximum {max_value}. Clamped.",
            )
        )
        return max_value

    return value


def _make_unique_patient_id(patient_id: str, seen_patient_ids: Dict[str, int]) -> str:
    """Ensure patient IDs are unique inside one imported cohort."""
    if patient_id not in seen_patient_ids:
        seen_patient_ids[patient_id] = 1
        return patient_id

    seen_patient_ids[patient_id] += 1
    return f"{patient_id}_{seen_patient_ids[patient_id]}"


def get_available_cohorts(data_dir: Path | None = None) -> List[Path]:
    """List available CSV cohort files in the data directory.

    Args:
        data_dir: Directory to search. Defaults to data/cohorts/.

    Returns:
        List of Path objects for available CSV files.
    """
    if data_dir is None:
        data_dir = Path(__file__).parent.parent.parent.parent / "data" / "cohorts"

    if not data_dir.exists():
        return []

    return sorted(data_dir.glob("*.csv"))
