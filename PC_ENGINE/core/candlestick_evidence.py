from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from PC_ENGINE.core.candlestick_patterns import CandlestickPatternEngine, PatternMatch


@dataclass(frozen=True)
class CandlestickPattern:
    name: str
    direction: str
    score: float
    confidence: float
    index: int


@dataclass(frozen=True)
class CandlestickEvidence:
    bias: float
    confidence: float
    dominant: str
    patterns: tuple[CandlestickPattern, ...]
    paper_only: bool = True


_SCORE_BY_PATTERN = {
    "doji": 0.0,
    "dragonfly_doji": 0.62,
    "gravestone_doji": -0.62,
    "spinning_top": 0.0,
    "hammer": 0.72,
    "inverted_hammer": 0.58,
    "hanging_man": -0.68,
    "shooting_star": -0.72,
    "bullish_marubozu": 0.78,
    "bearish_marubozu": -0.78,
    "bullish_engulfing": 0.86,
    "bearish_engulfing": -0.86,
    "piercing_line": 0.68,
    "dark_cloud_cover": -0.68,
    "bullish_harami": 0.64,
    "bearish_harami": -0.64,
    "tweezer_bottom": 0.60,
    "tweezer_top": -0.60,
    "morning_star": 0.82,
    "evening_star": -0.82,
    "three_inside_up": 0.70,
    "three_inside_down": -0.70,
    "three_white_soldiers": 0.70,
    "three_black_crows": -0.70,
    "rising_three_methods": 0.74,
    "falling_three_methods": -0.74,
}


def _valid_rows(rows: list[list[float]]) -> list[list[float]]:
    valid: list[list[float]] = []
    for row in rows:
        if len(row) < 5:
            continue
        try:
            values = [float(row[1]), float(row[2]), float(row[3]), float(row[4])]
        except (TypeError, ValueError):
            continue
        if not all(isfinite(v) for v in values):
            continue
        o, h, low, close = values
        if min(o, h, low, close) <= 0 or h < max(o, close) or low > min(o, close) or h <= low:
            continue
        valid.append(row)
    return valid


def _score(match: PatternMatch) -> float:
    if match.name in _SCORE_BY_PATTERN:
        return _SCORE_BY_PATTERN[match.name]
    if match.bias == "BULLISH":
        return round(match.confidence, 4)
    if match.bias == "BEARISH":
        return round(-match.confidence, 4)
    return 0.0


def _direction(score: float) -> str:
    if score > 0:
        return "BUY"
    if score < 0:
        return "SELL"
    return "HOLD"


def detect_candlestick_patterns(rows: list[list[float]]) -> list[CandlestickPattern]:
    """Return the canonical candlestick vocabulary used by PatternEngine.

    The PatternEngine is the single detector authority. This evidence layer
    converts its PAPER-only matches into the durable evidence representation,
    preventing the two layers from drifting into different pattern names or
    rules.
    """
    valid = _valid_rows(rows)
    if len(valid) < 3:
        return []

    matches = CandlestickPatternEngine({"enabled": True, "min_confidence": 0.70}).detect(valid)
    index = len(valid) - 1
    return [
        CandlestickPattern(
            name=match.name,
            direction=_direction(_score(match)),
            score=_score(match),
            confidence=match.confidence,
            index=index,
        )
        for match in matches
    ]


def analyze_candlesticks(rows: list[list[float]]) -> CandlestickEvidence:
    patterns = detect_candlestick_patterns(rows)
    if not patterns:
        return CandlestickEvidence(0.0, 0.0, "none", ())

    bullish = [p for p in patterns if p.score > 0]
    bearish = [p for p in patterns if p.score < 0]
    total = sum(p.score * p.confidence for p in patterns)
    contradiction = min(len(bullish), len(bearish))
    if contradiction:
        total *= max(0.0, 1.0 - 0.20 * contradiction)

    dominant = max(patterns, key=lambda p: abs(p.score) * p.confidence)
    confidence = min(
        1.0,
        0.45 * dominant.confidence + 0.55 * min(1.0, len(patterns) / 3.0),
    )
    return CandlestickEvidence(
        round(max(-1.0, min(1.0, total)), 4),
        round(confidence, 4),
        dominant.name,
        tuple(patterns),
    )
