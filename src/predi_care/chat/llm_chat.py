from __future__ import annotations

from dataclasses import dataclass

from predi_care.engine.brain_engine import DecisionPack
from predi_care.engine.brain_engine import explain_recommendation_chat


@dataclass
class ExpertChatService:
    """LLM chat facade: simulated mode now, API mode pluggable later."""

    mode: str = "simulated"

    def answer(self, question: str, decision_pack: DecisionPack) -> str:
        if self.mode == "simulated":
            return explain_recommendation_chat(question, decision_pack)

        return (
            "Mode API non configure pour l'instant. "
            "Activez une integration LLM et renseignez la configuration necessaire."
        )
