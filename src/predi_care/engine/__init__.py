"""Canonical engine exports (v4 default, v2 compatible)."""

from __future__ import annotations

from predi_care.engine.brain_engine import BrainEngineV4
from predi_care.engine.brain_engine import create_brain_engine as create_brain_engine_v4
from predi_care.engine.brain_engine_v2 import BrainEngineV2, DecisionResult
from predi_care.engine.brain_engine_v2 import create_brain_engine as create_brain_engine_v2
from predi_care.engine.mock_factory import (
    PRESET_SCENARIOS,
    generate_mock_cohort,
    generate_mock_patient,
    get_preset_scenario,
    list_preset_scenarios,
)
from predi_care.engine.patient_types import PatientInput
from predi_care.engine.v4_types import (
    AgentOutput,
    ConsensusReport,
    DataTwinProfile,
    EngineResultV4,
    SafetyCheckReport,
)


def create_brain_engine(version: str = "v4") -> BrainEngineV4 | BrainEngineV2:
    normalized = version.strip().lower()
    if normalized in {"v4", "latest"}:
        return create_brain_engine_v4("v4")
    if normalized in {"v2", "v1", "legacy"}:
        return create_brain_engine_v2("v2")
    raise ValueError(f"Unknown brain engine version: {version}")


__all__ = [
    "BrainEngineV4",
    "BrainEngineV2",
    "DecisionResult",
    "EngineResultV4",
    "DataTwinProfile",
    "AgentOutput",
    "ConsensusReport",
    "SafetyCheckReport",
    "create_brain_engine",
    "create_brain_engine_v4",
    "create_brain_engine_v2",
    "PatientInput",
    "generate_mock_patient",
    "generate_mock_cohort",
    "PRESET_SCENARIOS",
    "get_preset_scenario",
    "list_preset_scenarios",
]

