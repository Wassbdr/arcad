import pytest

from predi_care.engine.brain_engine_v2 import BrainEngineV2, create_brain_engine


def test_create_brain_engine_v2_returns_v2_instance() -> None:
    engine = create_brain_engine("v2")
    assert isinstance(engine, BrainEngineV2)


def test_create_brain_engine_v1_is_supported_alias() -> None:
    engine = create_brain_engine("v1")
    assert isinstance(engine, BrainEngineV2)


def test_create_brain_engine_version_is_case_insensitive() -> None:
    engine = create_brain_engine("V1")
    assert isinstance(engine, BrainEngineV2)


def test_create_brain_engine_rejects_unknown_version() -> None:
    with pytest.raises(ValueError, match="Unknown brain engine version"):
        create_brain_engine("legacy")
