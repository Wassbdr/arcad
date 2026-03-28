"""Canonical patient input types for the v2 decision pipeline."""

from __future__ import annotations

from typing import TypedDict


class _PatientInputRequired(TypedDict):
    """Required baseline variables for the decision engine."""

    ct_stage: str
    cn_stage: str
    cm_stage: str
    ace_baseline: float
    ace_current: float
    residual_tumor_ratio: float
    imaging_quality: str
    age: int
    performance_status: int


class PatientInput(_PatientInputRequired, total=False):
    """Extended clinical variables used by advanced heuristics and LLM context."""

    residual_size_cm: float
    distance_marge_anale: float
    delay_weeks_post_rct: int
    protocol_neoadjuvant: str
    emvi: bool
    mrtrg: int
    asa_score: int
    smoking: bool
    diabetes: bool
    albumin: float
    hemoglobin: float
    msi_status: str
    tumor_height_cm: float
    crm_distance_mm: float
    crm_status: str
