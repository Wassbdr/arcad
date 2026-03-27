from __future__ import annotations

from random import Random
from typing import List

from predi_care.engine.brain_engine import PatientInput


def generate_mock_patient(seed: int = 7) -> PatientInput:
    rng = Random(seed)

    ct_stage = rng.choice(["cT1", "cT2", "cT3", "cT4"])
    cn_stage = rng.choice(["cN0", "cN1", "cN2"])
    cm_stage = rng.choice(["cM0", "cM0", "cM0", "cM1"])

    age = rng.randint(38, 84)
    performance_status = rng.choice([0, 1, 1, 2, 2, 3])

    ace_baseline = round(rng.uniform(2.5, 28.0), 1)
    ace_current = round(max(0.2, ace_baseline * rng.uniform(0.25, 1.05)), 1)

    residual_tumor_ratio = round(rng.uniform(2.0, 68.0), 1)
    imaging_quality = rng.choice(["Elevee", "Moyenne"])

    return {
        "ct_stage": ct_stage,
        "cn_stage": cn_stage,
        "cm_stage": cm_stage,
        "ace_baseline": ace_baseline,
        "ace_current": ace_current,
        "residual_tumor_ratio": residual_tumor_ratio,
        "imaging_quality": imaging_quality,
        "age": age,
        "performance_status": performance_status,
    }


def generate_mock_cohort(size: int = 16, base_seed: int = 10) -> List[PatientInput]:
    return [generate_mock_patient(seed=base_seed + idx) for idx in range(size)]


# Scenarios cliniques predefinis pour demo et tests
PRESET_SCENARIOS: dict[str, PatientInput] = {
    "Candidat ideal Watch & Wait": {
        "ct_stage": "cT2",
        "cn_stage": "cN0",
        "cm_stage": "cM0",
        "ace_baseline": 6.5,
        "ace_current": 2.0,
        "residual_tumor_ratio": 8.0,
        "imaging_quality": "Elevee",
        "age": 52,
        "performance_status": 0,
    },
    "Indication chirurgicale claire": {
        "ct_stage": "cT4",
        "cn_stage": "cN2",
        "cm_stage": "cM0",
        "ace_baseline": 18.0,
        "ace_current": 14.5,
        "residual_tumor_ratio": 42.0,
        "imaging_quality": "Elevee",
        "age": 68,
        "performance_status": 1,
    },
    "Cas de conflit decisionnel": {
        "ct_stage": "cT2",
        "cn_stage": "cN0",
        "cm_stage": "cM0",
        "ace_baseline": 8.0,
        "ace_current": 7.2,
        "residual_tumor_ratio": 12.0,
        "imaging_quality": "Moyenne",
        "age": 61,
        "performance_status": 0,
    },
    "Metastatique (cM1)": {
        "ct_stage": "cT3",
        "cn_stage": "cN1",
        "cm_stage": "cM1",
        "ace_baseline": 22.0,
        "ace_current": 18.0,
        "residual_tumor_ratio": 35.0,
        "imaging_quality": "Elevee",
        "age": 72,
        "performance_status": 2,
    },
    "Reponse biologique excellente": {
        "ct_stage": "cT3",
        "cn_stage": "cN1",
        "cm_stage": "cM0",
        "ace_baseline": 15.0,
        "ace_current": 3.5,
        "residual_tumor_ratio": 18.0,
        "imaging_quality": "Elevee",
        "age": 58,
        "performance_status": 0,
    },
}


def get_preset_scenario(name: str) -> PatientInput | None:
    """Retrieve a preset clinical scenario by name."""
    return PRESET_SCENARIOS.get(name)


def list_preset_scenarios() -> list[str]:
    """List all available preset scenario names."""
    return list(PRESET_SCENARIOS.keys())
