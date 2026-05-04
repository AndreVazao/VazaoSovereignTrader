from __future__ import annotations

from dataclasses import dataclass

from PC_ENGINE.ai_council.decision_mapper import map_rating_to_score_delta


@dataclass
class AICouncilOpinion:
    symbol: str
    rating: str = "HOLD"
    confidence: float = 0.0
    rationale: str = "ai council disabled"

    @property
    def score_delta(self) -> float:
        return map_rating_to_score_delta(self.rating, self.confidence)


class DisabledAICouncil:
    def analyse(self, symbol: str, context: dict) -> AICouncilOpinion:
        return AICouncilOpinion(symbol=symbol)
