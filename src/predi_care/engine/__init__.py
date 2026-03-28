"""Canonical engine exports for the v2 decision pipeline."""

from .brain_engine_v2 import BrainEngineV2, DecisionResult, create_brain_engine
from .mock_factory import PRESET_SCENARIOS, generate_mock_cohort, generate_mock_patient
from .mock_factory import get_preset_scenario, list_preset_scenarios
from .patient_types import PatientInput

__all__ = [
    "BrainEngineV2",
    "DecisionResult",
    "create_brain_engine",
    "PatientInput",
    "generate_mock_patient",
    "generate_mock_cohort",
    "PRESET_SCENARIOS",
    "get_preset_scenario",
    "list_preset_scenarios",
]
