"""Dataset v3 adapter and Digital Twin profile builder."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from predi_care.engine.patient_types import PatientInput
from predi_care.engine.v4_types import DataTwinProfile, FeatureTrace


V3_CRITICAL_COLUMNS = {
    "baseline_cT",
    "baseline_cN",
    "cM",
    "cea_baseline_ng_ml",
    "cea_current_ng_ml",
    "residual_tumor_ratio_native",
    "imaging_quality",
    "age_years",
    "ecog_score",
}


def _to_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "y", "oui", "current"}:
        return True
    if normalized in {"0", "false", "no", "n", "non", "never", "former"}:
        return False
    return default


def _to_float(value: Any, default: float | None = None) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value: Any, default: int | None = None) -> int | None:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _normalize_imaging_quality(raw: Any) -> str:
    normalized = str(raw).strip().lower()
    mapping = {
        "good": "Elevee",
        "high": "Elevee",
        "elevee": "Elevee",
        "acceptable": "Moyenne",
        "medium": "Moyenne",
        "moyenne": "Moyenne",
        "limited": "Basse",
        "low": "Basse",
        "basse": "Basse",
    }
    return mapping.get(normalized, "Moyenne")


def _normalize_msi(raw: Any) -> str:
    normalized = str(raw).strip().lower()
    if normalized in {"msi_h_dmmr", "dmmr/msi-h", "dmmr_msi-h", "dmmr"}:
        return "dMMR/MSI-H"
    if normalized in {"mss_pmmr", "mss", "mss/msi-l", "msi-l"}:
        return "MSS/MSI-L"
    return "Non teste"


def _normalize_asa(raw: Any) -> int:
    normalized = str(raw).strip().upper()
    mapping = {"I": 1, "II": 2, "III": 3, "IV": 4}
    if normalized in mapping:
        return mapping[normalized]
    parsed = _to_int(raw, default=2)
    if parsed is None:
        return 2
    return min(4, max(1, parsed))


def _derive_crm_status(crm_distance_mm: float) -> str:
    if crm_distance_mm < 1.0:
        return "positive"
    if crm_distance_mm < 2.0:
        return "threatened"
    return "negative"


def _derive_trg_from_residual_percent(residual_ratio: float) -> int:
    # v4 convention: 1 best, 5 worst (aligned with mrTRG-like scale)
    if residual_ratio <= 5:
        return 1
    if residual_ratio <= 15:
        return 2
    if residual_ratio <= 40:
        return 3
    if residual_ratio <= 70:
        return 4
    return 5


def _derive_clinical_response(residual_ratio: float) -> str:
    if residual_ratio <= 5:
        return "complete"
    if residual_ratio <= 15:
        return "near_complete"
    if residual_ratio <= 40:
        return "partial"
    return "non_response"


def _set_trace(
    traces: dict[str, FeatureTrace],
    key: str,
    value: Any,
    source: str,
    quality: str,
) -> None:
    traces[key] = FeatureTrace(value=value, source=source, quality=quality)


def _build_stubs(core: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    residual_size_cm = float(core.get("residual_size_cm", 0.0))
    ace_baseline = float(core.get("ace_baseline", 0.0))
    ace_current = float(core.get("ace_current", 0.0))
    ace_drop = 0.0
    if ace_baseline > 0:
        ace_drop = max(0.0, (ace_baseline - ace_current) / ace_baseline)

    imaging_stub = {
        "tumor_burden_index": min(1.0, residual_size_cm / 5.0),
        "regression_mm": max(0.0, (5.0 - residual_size_cm) * 10.0),
        "mesorectal_infiltration_index": 0.7 if core.get("emvi") else 0.3,
    }
    omics_stub = {
        "radio_resistance_signature": 0.25 if core.get("msi_status") == "dMMR/MSI-H" else 0.55,
        "chemo_sensitivity_signature": 0.75 if ace_drop >= 0.5 else 0.45,
        "microbiome_inflammation_index": 0.6 if core.get("smoking") else 0.35,
    }
    pros_stub = {
        "lars_score_projection": min(100.0, 20.0 + residual_size_cm * 15.0),
        "qol_index_projection": max(45.0, 90.0 - residual_size_cm * 8.0),
        "apa_activity_projection": max(20.0, 75.0 - float(core.get("ecog", 1)) * 12.0),
    }
    return imaging_stub, omics_stub, pros_stub


def _build_profile(
    patient_id: str,
    core: dict[str, Any],
    traces: dict[str, FeatureTrace],
    missing_inputs: list[str],
) -> DataTwinProfile:
    imaging_stub, omics_stub, pros_stub = _build_stubs(core)
    return DataTwinProfile(
        patient_id=patient_id,
        core_clinical=core,
        imaging_stub=imaging_stub,
        omics_stub=omics_stub,
        pros_stub=pros_stub,
        provenance=traces,
        missing_inputs=missing_inputs,
    )


def build_profile_from_patient_input(
    patient_input: PatientInput,
    patient_id: str = "MANUAL-001",
) -> DataTwinProfile:
    """Build a Digital Twin profile from app-level patient input."""
    traces: dict[str, FeatureTrace] = {}
    missing_inputs: list[str] = []

    residual_ratio = float(patient_input.get("residual_tumor_ratio", 30.0))
    residual_ratio = min(100.0, max(0.0, residual_ratio))
    residual_size_cm = float(patient_input.get("residual_size_cm", residual_ratio / 20.0))

    crm_mm = float(patient_input.get("crm_distance_mm", 5.0))
    core = {
        "ct_stage": str(patient_input.get("ct_stage", "cT3")),
        "cn_stage": str(patient_input.get("cn_stage", "cN0")),
        "cm_stage": str(patient_input.get("cm_stage", "cM0")),
        "age": int(patient_input.get("age", 62)),
        "ecog": int(patient_input.get("performance_status", 1)),
        "asa_score": int(patient_input.get("asa_score", 2)),
        "ace_baseline": float(patient_input.get("ace_baseline", 5.0)),
        "ace_current": float(patient_input.get("ace_current", 3.0)),
        "residual_tumor_ratio": residual_ratio,
        "residual_size_cm": residual_size_cm,
        "trg": int(patient_input.get("mrtrg", _derive_trg_from_residual_percent(residual_ratio))),
        "clinical_response": str(
            patient_input.get("clinical_response", _derive_clinical_response(residual_ratio))
        ),
        "imaging_quality": _normalize_imaging_quality(patient_input.get("imaging_quality", "Moyenne")),
        "distance_marge_anale": float(patient_input.get("distance_marge_anale", 8.0)),
        "delay_weeks_post_rct": int(patient_input.get("delay_weeks_post_rct", 8)),
        "protocol_neoadjuvant": str(patient_input.get("protocol_neoadjuvant", "RCT standard")),
        "emvi": _to_bool(patient_input.get("emvi", False)),
        "mrtrg": int(patient_input.get("mrtrg", 3)),
        "smoking": _to_bool(patient_input.get("smoking", False)),
        "diabetes": _to_bool(patient_input.get("diabetes", False)),
        "albumin": float(patient_input.get("albumin", 40.0)),
        "hemoglobin": float(patient_input.get("hemoglobin", 13.0)),
        "msi_status": _normalize_msi(patient_input.get("msi_status", "Non teste")),
        "crm_distance_mm": crm_mm,
        "crm_status": str(patient_input.get("crm_status", _derive_crm_status(crm_mm))),
    }

    for key, value in core.items():
        _set_trace(traces, key, value, "dataset", "observed")

    return _build_profile(patient_id, core, traces, missing_inputs)


def build_profile_from_v3_row(row: Mapping[str, Any]) -> DataTwinProfile:
    """Build a Digital Twin profile from one dataset v3 row."""
    traces: dict[str, FeatureTrace] = {}
    missing_inputs: list[str] = []
    patient_id = str(row.get("patient_id", "UNKNOWN"))

    def observe(name: str, value: Any, default: Any) -> Any:
        if value is None or value == "":
            missing_inputs.append(name)
            _set_trace(traces, name, default, "simulated", "imputed")
            return default
        _set_trace(traces, name, value, "dataset", "observed")
        return value

    ct_stage = str(observe("ct_stage", row.get("baseline_cT"), "cT3"))
    cn_stage = str(observe("cn_stage", row.get("baseline_cN"), "cN0"))
    cm_stage = str(observe("cm_stage", row.get("cM"), "cM0"))
    age = int(observe("age", _to_int(row.get("age_years")), 62))
    ecog = int(observe("ecog", _to_int(row.get("ecog_score")), 1))
    asa_score = int(observe("asa_score", _normalize_asa(row.get("asa_class")), 2))
    ace_baseline = float(observe("ace_baseline", _to_float(row.get("cea_baseline_ng_ml")), 5.0))
    ace_current = float(observe("ace_current", _to_float(row.get("cea_current_ng_ml")), 3.0))

    native_ratio = _to_float(row.get("residual_tumor_ratio_native"))
    if native_ratio is None:
        residual_ratio = float(observe("residual_tumor_ratio", None, 30.0))
    else:
        residual_ratio = min(100.0, max(0.0, native_ratio * 100.0))
        _set_trace(traces, "residual_tumor_ratio", residual_ratio, "derived", "observed")

    residual_cm = _to_float(row.get("restaging_residual_lesion_cm"))
    if residual_cm is None:
        residual_cm = residual_ratio / 20.0
        _set_trace(traces, "residual_size_cm", residual_cm, "derived", "imputed")
        missing_inputs.append("residual_size_cm")
    else:
        _set_trace(traces, "residual_size_cm", residual_cm, "dataset", "observed")

    mrtrg_raw = _to_int(row.get("restaging_mrTRG"))
    if mrtrg_raw is None:
        trg = _derive_trg_from_residual_percent(residual_ratio)
        _set_trace(traces, "trg", trg, "derived", "imputed")
        missing_inputs.append("trg")
    else:
        trg = max(1, min(5, mrtrg_raw))
        _set_trace(traces, "trg", trg, "dataset", "observed")

    clinical_response_raw = row.get("restaging_endoscopy_response")
    if clinical_response_raw in {"CCR", "ICR", "NCR"}:
        clinical_response = {"CCR": "complete", "ICR": "near_complete", "NCR": "partial"}[
            str(clinical_response_raw)
        ]
        _set_trace(traces, "clinical_response", clinical_response, "derived", "observed")
    else:
        clinical_response = _derive_clinical_response(residual_ratio)
        _set_trace(traces, "clinical_response", clinical_response, "derived", "imputed")
        missing_inputs.append("clinical_response")

    imaging_quality = _normalize_imaging_quality(row.get("imaging_quality", "acceptable"))
    _set_trace(traces, "imaging_quality", imaging_quality, "derived", "observed")

    distance_marge_anale = float(
        observe("distance_marge_anale", _to_float(row.get("tumor_distance_from_anal_verge_cm")), 8.0)
    )
    delay_weeks = int(
        observe("delay_weeks_post_rct", _to_int(row.get("initial_restaging_weeks_post_crt")), 8)
    )
    protocol = str(
        observe("protocol_neoadjuvant", row.get("concomitant_chemotherapy"), "RCT standard")
    )
    emvi = _to_bool(observe("emvi", row.get("baseline_emvi"), False))
    smoking_status = str(row.get("smoking_status", "never")).strip().lower()
    smoking = smoking_status == "current"
    _set_trace(traces, "smoking", smoking, "derived", "observed")
    diabetes = _to_bool(observe("diabetes", row.get("diabetes"), False))
    albumin = float(observe("albumin", _to_float(row.get("albumin_g_l")), 40.0))
    hemoglobin = float(observe("hemoglobin", _to_float(row.get("hemoglobin_g_dl")), 13.0))
    msi_status = _normalize_msi(observe("msi_status", row.get("msi_status"), "MSS_pMMR"))
    crm_distance = float(observe("crm_distance_mm", _to_float(row.get("baseline_mri_crm_mm")), 5.0))
    crm_status = _derive_crm_status(crm_distance)
    _set_trace(traces, "crm_status", crm_status, "derived", "observed")

    core = {
        "ct_stage": ct_stage,
        "cn_stage": cn_stage,
        "cm_stage": cm_stage,
        "age": age,
        "ecog": ecog,
        "asa_score": asa_score,
        "ace_baseline": ace_baseline,
        "ace_current": ace_current,
        "residual_tumor_ratio": residual_ratio,
        "residual_size_cm": residual_cm,
        "trg": trg,
        "clinical_response": clinical_response,
        "imaging_quality": imaging_quality,
        "distance_marge_anale": distance_marge_anale,
        "delay_weeks_post_rct": delay_weeks,
        "protocol_neoadjuvant": protocol,
        "emvi": emvi,
        "mrtrg": trg,
        "smoking": smoking,
        "diabetes": diabetes,
        "albumin": albumin,
        "hemoglobin": hemoglobin,
        "msi_status": msi_status,
        "crm_distance_mm": crm_distance,
        "crm_status": crm_status,
    }

    for key, value in core.items():
        if key not in traces:
            _set_trace(traces, key, value, "dataset", "observed")

    return _build_profile(patient_id, core, traces, missing_inputs)


def validate_v3_columns(columns: set[str]) -> list[str]:
    """Return missing critical columns for the v3 cohort shape."""
    missing = [column for column in sorted(V3_CRITICAL_COLUMNS) if column not in columns]
    return missing

