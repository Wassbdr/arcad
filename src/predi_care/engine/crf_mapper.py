"""Mapper module: Convert legacy PatientInput to CRFInput format.

This module bridges the existing PREDI-Care data model with the new
high-fidelity CRF simulator format.
"""

from __future__ import annotations

from typing import Any

from predi_care.engine.patient_types import PatientInput
from predi_care.engine.crf_simulator import CRFInput


def map_patient_input_to_crf(patient: PatientInput) -> CRFInput:
    """Convert legacy PatientInput to CRFInput format.

    Mapping Logic:
    - ct_stage → yct_stage (assuming post-neoadjuvant staging)
    - cn_stage → ycn_stage
    - residual_tumor_ratio → derive TRG score
    - imaging_quality → mri_quality
    - Other fields map directly or use defaults

    Args:
        patient: Legacy PatientInput dict (TypedDict)

    Returns:
        CRFInput object ready for CRF simulation
    """

    # === TNM Staging (direct mapping) ===
    # Assuming ct_stage represents post-neoadjuvant ycT
    yct_stage = _map_ct_to_yct(patient["ct_stage"])
    ycn_stage = _map_cn_to_ycn(patient["cn_stage"])

    patient_payload: dict[str, Any] = dict(patient)

    residual_ratio = float(patient_payload.get("residual_tumor_ratio", patient["residual_tumor_ratio"]))
    imaging_quality = str(patient_payload.get("imaging_quality", patient["imaging_quality"]))

    # === TRG Score (derive from residual_tumor_ratio) ===
    # TRG 1-5 scale:
    # 1 = Complete response (0% residual)
    # 2 = Near-complete (<10% residual)
    # 3 = Moderate (10-50% residual)
    # 4 = Minimal (<50% regression)
    # 5 = No response
    trg_score = _derive_trg_from_residual(residual_ratio)

    # === Digital Rectal Exam (estimate from residual_tumor_ratio) ===
    # If residual very low, assume normal TR
    if residual_ratio < 10:
        digital_rectal_exam = "normal"
    elif residual_ratio < 50:
        digital_rectal_exam = "not_done"  # Uncertain
    else:
        digital_rectal_exam = "abnormal"

    # === ASA Score (use direct value if available, otherwise estimate) ===
    asa_score = patient.get("asa_score") or _estimate_asa_from_age_ecog(patient["age"], patient["performance_status"])

    # === ECOG (direct mapping) ===
    ecog_performance = patient["performance_status"]

    # === Tumor Height (use distance_marge_anale if provided) ===
    tumor_height_cm = float(patient.get("distance_marge_anale", 8.0))
    tumor_height_cm = max(0.0, min(15.0, tumor_height_cm))

    # === Age (direct) ===
    age = patient["age"]

    # === ACE (direct) ===
    ace_baseline = patient["ace_baseline"]
    ace_current = patient["ace_current"]

    # === CRM Status (estimate from residual, imaging, and EMVI) ===
    crm_status = _estimate_crm_status(
        residual_ratio,
        imaging_quality,
        patient.get("emvi", False),
    )

    # === MRI Quality (direct mapping) ===
    mri_quality = _map_imaging_quality(imaging_quality)

    return CRFInput(
        yct_stage=yct_stage,
        ycn_stage=ycn_stage,
        trg_score=trg_score,
        digital_rectal_exam=digital_rectal_exam,
        asa_score=asa_score,
        ecog_performance=ecog_performance,
        tumor_height_cm=tumor_height_cm,
        age=age,
        ace_baseline=ace_baseline,
        ace_current=ace_current,
        crm_status=crm_status,
        mri_quality=mri_quality,
    )


def _map_ct_to_yct(ct_stage: str) -> str:
    """Map cT stage to ycT (post-neoadjuvant) stage.

    In practice, ycT is often lower than pre-treatment cT due to
    neoadjuvant therapy. For mapping, we assume ct_stage represents ycT.
    """
    mapping = {
        "cT1": "ycT1",
        "cT2": "ycT2",
        "cT3": "ycT3",
        "cT4": "ycT4",
    }
    return mapping.get(ct_stage, "ycT2")  # Default to ycT2


def _map_cn_to_ycn(cn_stage: str) -> str:
    """Map cN stage to ycN (post-neoadjuvant) stage."""
    mapping = {
        "cN0": "ycN0",
        "cN1": "ycN1",
        "cN2": "ycN2",
    }
    return mapping.get(cn_stage, "ycN0")  # Default to ycN0


def _derive_trg_from_residual(residual_ratio: float) -> int:
    """Derive TRG score (1-5) from residual tumor ratio (%).

    TRG Mandard Scale:
    - TRG 1: Complete regression (0% viable tumor)
    - TRG 2: Rare residual cells (<10%)
    - TRG 3: Increase in fibrosis with residual tumor (10-50%)
    - TRG 4: Dominant tumor mass (>50%)
    - TRG 5: Absence of regression
    """
    if residual_ratio == 0:
        return 1  # Complete response
    elif residual_ratio < 10:
        return 2  # Near-complete
    elif residual_ratio < 50:
        return 3  # Moderate regression
    elif residual_ratio < 80:
        return 4  # Minimal regression
    else:
        return 5  # No response


def _estimate_asa_from_age_ecog(age: int, ecog: int) -> int:
    """Estimate ASA score from age and ECOG performance status.

    ASA Scale:
    - ASA 1: Healthy patient
    - ASA 2: Mild systemic disease
    - ASA 3: Severe systemic disease
    - ASA 4: Life-threatening disease

    Heuristic:
    - ECOG 0 + age < 60 → ASA 1
    - ECOG 0-1 + age < 75 → ASA 2
    - ECOG 2 or age ≥ 75 → ASA 3
    - ECOG ≥ 3 → ASA 4
    """
    if ecog == 0 and age < 60:
        return 1
    elif ecog <= 1 and age < 75:
        return 2
    elif ecog == 2 or age >= 75:
        return 3
    else:
        return 4


def _estimate_crm_status(residual_ratio: float, imaging_quality: str, emvi: bool = False) -> str:
    """Estimate CRM (Circumferential Resection Margin) status.

    CRM is critical for surgery outcomes:
    - Negative: >2mm clearance
    - Threatened: 1-2mm clearance
    - Positive: <1mm clearance

    Heuristic based on residual tumor burden, imaging, and EMVI.
    """
    # EMVI positive is a strong indicator of threatened/positive CRM
    if emvi and residual_ratio >= 30:
        return "positive"
    if emvi:
        return "threatened"
    if residual_ratio < 10 and imaging_quality == "Elevee":
        return "threatened"  # Borderline

    return "threatened"  # Conservative estimate


def _map_imaging_quality(imaging_quality: str) -> str:
    """Map imaging quality to CRF format.

    Mapping:
    - "Elevee" → "high"
    - "Moyenne" → "medium"
    - "Basse" → "low"
    """
    mapping = {
        "Elevee": "high",
        "Moyenne": "medium",
        "Basse": "low",
    }
    return mapping.get(imaging_quality, "medium")  # Default to medium


def _normalize_crm_status(value: Any) -> str | None:
    """Normalize an optional crm_status hint value."""
    if value is None:
        return None

    normalized = str(value).strip().lower()
    if normalized in {"negative", "threatened", "positive"}:
        return normalized
    return None


def _coerce_optional_float(value: Any, default: float | None) -> float | None:
    """Coerce optional scalar values to float with safe default fallback."""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
