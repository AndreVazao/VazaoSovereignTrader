from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Bias = Literal["BULLISH", "BEARISH", "NEUTRAL"]


@dataclass(frozen=True)
class PatternMatch:
    name: str
    bias: Bias
    confidence: float
    confirmation_needed: bool = True


class CandlestickPatternEngine:
    """Evidence-weighted candlestick detector.

    Patterns are treated as context/confirmation, never as standalone orders.
    This is deliberate: candlesticks can fail frequently in noisy markets,
    especially on very short crypto timeframes.
    """

    def __init__(self, settings: dict | None = None):
        self.settings = settings or {}
        self.enabled = bool(self.settings.get("enabled", True))
        self.min_confidence = float(self.settings.get("min_confidence", 0.70))

    @staticmethod
    def _candle(c: list[float]) -> tuple[float, float, float, float]:
        return float(c[1]), float(c[2]), float(c[3]), float(c[4])

    @staticmethod
    def _parts(c: list[float]) -> tuple[float, float, float, float, float]:
        o, h, l, cl = CandlestickPatternEngine._candle(c)
        rng = max(h - l, 1e-12)
        body = abs(cl - o)
        upper = h - max(o, cl)
        lower = min(o, cl) - l
        return rng, body, upper, lower, cl - o

    @staticmethod
    def _trend(closes: list[float], lookback: int = 8) -> int:
        if len(closes) < lookback:
            return 0
        a = closes[-lookback]
        b = closes[-1]
        if a <= 0:
            return 0
        change = (b - a) / a
        if change > 0.002:
            return 1
        if change < -0.002:
            return -1
        return 0

    def detect(self, ohlcv: list[list[float]]) -> list[PatternMatch]:
        if not self.enabled or len(ohlcv) < 3:
            return []

        matches: list[PatternMatch] = []
        last = ohlcv[-1]
        prev = ohlcv[-2]
        prev2 = ohlcv[-3]
        rng, body, upper, lower, direction = self._parts(last)
        trend = self._trend([float(c[4]) for c in ohlcv])

        # Single-candle patterns. Their direction depends on market context.
        if body <= rng * 0.10:
            if upper <= rng * 0.15 and lower >= rng * 0.60:
                matches.append(PatternMatch("dragonfly_doji", "BULLISH", 0.86))
            elif lower <= rng * 0.15 and upper >= rng * 0.60:
                matches.append(PatternMatch("gravestone_doji", "BEARISH", 0.86))
            else:
                matches.append(PatternMatch("doji", "NEUTRAL", 0.70))

        if body > 0:
            hammer_shape = lower >= body * 2.0 and upper <= body * 0.35 and max(last[1], last[4]) >= last[3] + rng * 0.55
            if hammer_shape:
                if trend < 0:
                    matches.append(PatternMatch("hammer", "BULLISH", 0.88))
                elif trend > 0:
                    matches.append(PatternMatch("hanging_man", "BEARISH", 0.82))

        # Two-candle engulfing patterns, using real bodies rather than shadows.
        po, ph, pl, pc = self._candle(prev)
        co, ch, cl, cc = self._candle(last)
        prev_body = abs(pc - po)
        curr_body = abs(cc - co)
        if pc < po and cc > co and curr_body >= prev_body * 0.95 and co <= pc and cc >= po:
            matches.append(PatternMatch("bullish_engulfing", "BULLISH", 0.90))
        if pc > po and cc < co and curr_body >= prev_body * 0.95 and co >= pc and cc <= po:
            matches.append(PatternMatch("bearish_engulfing", "BEARISH", 0.90))

        # Three-candle reversal/continuation patterns.
        o1, h1, l1, c1 = self._candle(prev2)
        o2, h2, l2, c2 = self._candle(prev)
        o3, h3, l3, c3 = self._candle(last)
        b1 = abs(c1 - o1)
        b2 = abs(c2 - o2)
        b3 = abs(c3 - o3)
        r1 = max(h1 - l1, 1e-12)
        if c1 < o1 and b1 >= r1 * 0.45 and b2 <= b1 * 0.45 and c3 > o3 and c3 >= (o1 + c1) / 2:
            matches.append(PatternMatch("morning_star", "BULLISH", 0.88))

        if all(self._candle(c)[3] > self._candle(c)[0] for c in (prev2, prev, last)):
            opens_inside = o2 <= c1 and o2 >= o1 and o3 <= c2 and o3 >= o2
            higher_closes = c2 > c1 and c3 > c2
            if opens_inside and higher_closes and min(b1, b2, b3) > 0:
                matches.append(PatternMatch("three_white_soldiers", "BULLISH", 0.91))

        if all(self._candle(c)[3] < self._candle(c)[0] for c in (prev2, prev, last)):
            opens_inside = o2 >= c1 and o2 <= o1 and o3 >= c2 and o3 <= o2
            lower_closes = c2 < c1 and c3 < c2
            if opens_inside and lower_closes and min(b1, b2, b3) > 0:
                matches.append(PatternMatch("three_black_crows", "BEARISH", 0.91))

        return [m for m in matches if m.confidence >= self.min_confidence]

    def evaluate(self, ohlcv: list[list[float]]) -> tuple[float, list[str], list[PatternMatch]]:
        matches = self.detect(ohlcv)
        if not matches:
            return 0.0, [], []
        weighted = 0.0
        total = 0.0
        for m in matches:
            if m.bias == "BULLISH":
                weighted += m.confidence
                total += m.confidence
            elif m.bias == "BEARISH":
                weighted -= m.confidence
                total += m.confidence
        bias = max(-1.0, min(1.0, weighted / total if total else 0.0))
        return round(bias, 4), [m.name for m in matches], matches
