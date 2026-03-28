from __future__ import annotations

from predi_care.engine import llm_client


def _sample_response() -> llm_client.MedicalLLMResponse:
    return llm_client._validate_and_parse(  # type: ignore[attr-defined]
        {
            "surgery": {
                "recurrence_local_2y": 6.0,
                "recurrence_local_5y": 8.0,
                "recurrence_systemic_2y": 18.0,
                "survival_dfs_2y": 84.0,
                "survival_dfs_5y": 73.0,
                "complication_rate": 16.0,
                "lars_risk": 24.0,
                "colostomy_risk": 8.0,
                "r0_probability": 93.0,
                "narrative_fr": "text",
            },
            "watch_wait": {
                "regrowth_2y": 22.0,
                "regrowth_5y": 28.0,
                "salvage_surgery_success": 88.0,
                "systemic_relapse_if_regrowth": 20.0,
                "survival_dfs_2y": 82.0,
                "survival_dfs_5y": 71.0,
                "organ_preservation_2y": 77.0,
                "surveillance_burden": "moderate",
                "narrative_fr": "text",
            },
            "recommendation": "surgery",
            "recommendation_rationale": "text",
            "uncertainty_level": "moderate",
            "uncertainty_reason": "text",
            "clinical_alerts": [],
            "key_factors": [],
            "patient_friendly_summary": "text",
        }
    )


def test_forced_heuristic_runtime(monkeypatch) -> None:
    monkeypatch.setenv("LLM_FORCE_HEURISTIC", "1")
    result = llm_client.call_medical_llm_with_runtime({"patient_id": "forced"})
    assert result.mode_runtime == "heuristic"
    assert result.response is None


def test_openai_failure_falls_back_to_alt(monkeypatch) -> None:
    monkeypatch.delenv("LLM_FORCE_HEURISTIC", raising=False)
    monkeypatch.setattr(llm_client, "_get_openai_api_key", lambda: "openai-key")
    monkeypatch.setattr(llm_client, "_get_alt_api_key", lambda: "alt-key")
    llm_client._cache.clear()  # type: ignore[attr-defined]
    for _state in llm_client._circuits.values():  # type: ignore[attr-defined]
        _state.failures = 0
        _state.opened_at = None

    def _fake_call_model(*, api_key, base_url, model, patient_data):  # type: ignore[no-untyped-def]
        if api_key == "openai-key":
            raise RuntimeError("openai down")
        return _sample_response()

    monkeypatch.setattr(llm_client, "_call_model", _fake_call_model)
    result = llm_client.call_medical_llm_with_runtime({"patient_id": "fallback-test"})
    assert result.mode_runtime == "alt_llm"
    assert result.response is not None


def test_legacy_call_returns_none_without_any_key(monkeypatch) -> None:
    monkeypatch.setattr(llm_client, "_get_api_key", lambda: None)
    assert llm_client.call_medical_llm({"patient_id": "legacy-no-key"}) is None
