from __future__ import annotations

RATING_WEIGHTS = {
    "BUY": 2.0,
    "OVERWEIGHT": 1.0,
    "HOLD": 0.0,
    "UNDERWEIGHT": -1.0,
    "SELL": -2.0,
}


def map_rating_to_score_delta(rating: str, confidence: float = 0.5) -> float:
    rating = rating.strip().upper()
    base = RATING_WEIGHTS.get(rating, 0.0)
    confidence = max(0.0, min(1.0, confidence))
    return base * confidence
