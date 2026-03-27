from predi_care.chat.llm_chat import ExpertChatService
from predi_care.engine.brain_engine import PatientInput, run_multimodal_pipeline


def test_expert_chat_simulated_mode_returns_answer() -> None:
    payload: PatientInput = {
        "ct_stage": "cT3",
        "cn_stage": "cN1",
        "cm_stage": "cM0",
        "ace_baseline": 12.0,
        "ace_current": 4.2,
        "residual_tumor_ratio": 25.0,
        "imaging_quality": "Elevee",
        "age": 59,
        "performance_status": 1,
    }
    pack = run_multimodal_pipeline(payload)
    service = ExpertChatService(mode="simulated")
    answer = service.answer("Pourquoi la chirurgie ?", pack)
    assert isinstance(answer, str)
    assert len(answer) > 8


def test_expert_chat_can_explain_uncertainty() -> None:
    payload: PatientInput = {
        "ct_stage": "cT1",
        "cn_stage": "cN0",
        "cm_stage": "cM0",
        "ace_baseline": 12.0,
        "ace_current": 10.4,
        "residual_tumor_ratio": 8.0,
        "imaging_quality": "Moyenne",
        "age": 57,
        "performance_status": 1,
    }
    pack = run_multimodal_pipeline(payload)
    service = ExpertChatService(mode="simulated")
    answer = service.answer("Y a-t-il un conflit ou une incertitude ?", pack)
    assert "incertitude" in answer.lower() or "conflit" in answer.lower()
