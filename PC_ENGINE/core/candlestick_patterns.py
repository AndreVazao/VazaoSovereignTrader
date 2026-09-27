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

    Candlestick patterns are context features, never standalone orders.
    """

    def __init__(self, settings: dict | None = None):
        self.settings = settings or {}
        self.enabled = bool(self.settings.get("enabled", True))
        self.min_confidence = float(self.settings.get("min_confidence", 0.70))

    @staticmethod
    def _candle(c: list[float]) -> tuple[float, float, float, float]:
        if len(c) < 5:
            raise ValueError("OHLCV row must contain at least five fields")
        return float(c[1]), float(c[2]), float(c[3]), float(c[4])

    @staticmethod
    def _parts(c: list[float]) -> tuple[float, float, float, float, float]:
        o, h, l, cl = CandlestickPatternEngine._candle(c)
        if not all(__import__("math").isfinite(v) for v in (o, h, l, cl)):
            raise ValueError("OHLCV contains non-finite values")
        rng = max(h - l, 1e-12)
        body = abs(cl - o)
        upper = h - max(o, cl)
        lower = min(o, cl) - l
        return rng, body, upper, lower, cl - o

    @staticmethod
    def _trend(closes: list[float], lookback: int = 8) -> int:
        if len(closes) < 3:
            return 0
        effective = min(lookback, len(closes))
        a = closes[-effective]
        b = closes[-1]
        if a <= 0:
            return 0
        change = (b - a) / a
        if change > 0.002:
            return 1
        if change < -0.002:
            return -1
        return 0

    @staticmethod
    def _inside_body(previous: tuple[float, float, float, float], current: tuple[float, float, float, float]) -> bool:
        po, _, _, pc = previous
        co, _, _, cc = current
        return min(po, pc) <= min(co, cc) and max(co, cc) <= max(po, pc)

    def _engulfing(self, prev: list[float], last: list[float]) -> PatternMatch | None:
        po, _, _, pc = self._candle(prev)
        co, _, _, cc = self._candle(last)
        prev_body = abs(pc - po)
        curr_body = abs(cc - co)
        if prev_body <= 0 or curr_body < prev_body * 0.95:
            return None
        if pc < po and cc > co and co <= pc and cc >= po:
            return PatternMatch("bullish_engulfing", "BULLISH", 0.90)
        if pc > po and cc < co and co >= pc and cc <= po:
            return PatternMatch("bearish_engulfing", "BEARISH", 0.90)
        return None

    def _two_candle_patterns(self, prev: list[float], last: list[float]) -> list[PatternMatch]:
        po, ph, pl, pc = self._candle(prev)
        co, ch, cl, cc = self._candle(last)
        pr, pb, pu, p_lower, ps = self._parts(prev)
        rng, body, upper, lower, signed = self._parts(last)
        out: list[PatternMatch] = []

        engulfing = self._engulfing(prev, last)
        if engulfing is not None:
            out.append(engulfing)

        midpoint = (po + pc) / 2.0
        if ps < 0 and signed > 0 and cc > midpoint and cc < po:
            out.append(PatternMatch("piercing_line", "BULLISH", 0.78))
        if ps > 0 and signed < 0 and cc < midpoint and cc > po:
            out.append(PatternMatch("dark_cloud_cover", "BEARISH", 0.78))

        inside_body = self._inside_body((po, ph, pl, pc), (co, ch, cl, cc))
        if inside_body and body <= pb * 0.70:
            if ps < 0 and signed > 0:
                out.append(PatternMatch("bullish_harami", "BULLISH", 0.74))
            elif ps > 0 and signed < 0:
                out.append(PatternMatch("bearish_harami", "BEARISH", 0.74))

        tolerance = max(pr * 0.10, 1e-12)
        if abs(ph - ch) <= tolerance:
            if ps > 0 and signed < 0:
                out.append(PatternMatch("tweezer_top", "BEARISH", 0.76))
        if abs(pl - cl) <= tolerance:
            if ps < 0 and signed > 0:
                out.append(PatternMatch("tweezer_bottom", "BULLISH", 0.76))

        return out

    def detect(self, ohlcv: list[list[float]]) -> list[PatternMatch]:
        if not self.enabled or len(ohlcv) < 3:
            return []

        matches: list[PatternMatch] = []
        last = ohlcv[-1]
        prev = ohlcv[-2]
        prev2 = ohlcv[-3]
        rng, body, upper, lower, signed = self._parts(last)
        trend = self._trend([float(c[4]) for c in ohlcv])

        if body <= rng * 0.10:
            if upper <= rng * 0.15 and lower >= rng * 0.60:
                matches.append(PatternMatch("dragonfly_doji", "BULLISH", 0.86))
            elif lower <= rng * 0.15 and upper >= rng * 0.60:
                matches.append(PatternMatch("gravestone_doji", "BEARISH", 0.86))
            else:
                matches.append(PatternMatch("doji", "NEUTRAL", 0.70))
        elif body <= rng * 0.35 and upper >= rng * 0.25 and lower >= rng * 0.25:
            matches.append(PatternMatch("spinning_top", "NEUTRAL", 0.70))

        if body > 0:
            hammer_shape = lower >= body * 2.0 and upper <= body * 0.35 and max(last[1], last[4]) >= last[3] + rng * 0.55
            upper_rejection = upper >= body * 2.0 and lower <= body * 0.35 and min(last[1], last[4]) <= last[3] + rng * 0.45
            if hammer_shape:
                if trend < 0:
                    matches.append(PatternMatch("hammer", "BULLISH", 0.88))
                elif trend > 0:
                    matches.append(PatternMatch("hanging_man", "BEARISH", 0.82))
            if upper_rejection:
                if trend < 0:
                    matches.append(PatternMatch("inverted_hammer", "BULLISH", 0.80))
                elif trend > 0:
                    matches.append(PatternMatch("shooting_star", "BEARISH", 0.86))

        if body >= rng * 0.85 and upper <= rng * 0.08 and lower <= rng * 0.08:
            if signed > 0:
                matches.append(PatternMatch("bullish_marubozu", "BULLISH", 0.78))
            elif signed < 0:
                matches.append(PatternMatch("bearish_marubozu", "BEARISH", 0.78))

        pair_candidates = ((prev2, prev), (prev, last))
        seen_pairs: set[str] = set()
        for pair_prev, pair_last in pair_candidates:
            for pattern in self._two_candle_patterns(pair_prev, pair_last):
                if pattern.name not in seen_pairs:
                    matches.append(pattern)
                    seen_pairs.add(pattern.name)

        o1, h1, l1, c1 = self._candle(prev2)
        o2, h2, l2, c2 = self._candle(prev)
        o3, h3, l3, c3 = self._candle(last)
        b1 = abs(c1 - o1)
        b2 = abs(c2 - o2)
        b3 = abs(c3 - o3)
        r1 = max(h1 - l1, 1e-12)
        r2 = max(h2 - l2, 1e-12)
        r3 = max(h3 - l3, 1e-12)

        if c1 < o1 and b1 >= r1 * 0.45 and b2 <= b1 * 0.45 and c3 > o3 and c3 >= (o1 + c1) / 2:
            matches.append(PatternMatch("morning_star", "BULLISH", 0.88))
        if c1 > o1 and b1 >= r1 * 0.45 and b2 <= b1 * 0.45 and c3 < o3 and c3 <= (o1 + c1) / 2:
            matches.append(PatternMatch("evening_star", "BEARISH", 0.88))

        if c1 < o1 and c2 > o2 and c3 > o3 and c2 >= (o1 + c1) / 2 and c3 > h1:
            matches.append(PatternMatch("three_inside_up", "BULLISH", 0.82))
        if c1 > o1 and c2 < o2 and c3 < o3 and c2 <= (o1 + c1) / 2 and c3 < l1:
            matches.append(PatternMatch("three_inside_down", "BEARISH", 0.82))

        if all(self._candle(c)[3] > self._candle(c)[0] for c in (prev2, prev, last)):
            opens_inside = o2 <= c1 and o2 >= o1 and o3 <= c2 and o3 >= o2
            higher_closes = c2 > c1 and c3 > c2
            small_upper_wicks = (h1 - c1) <= r1 * 0.25 and (h2 - c2) <= r2 * 0.25 and (h3 - c3) <= r3 * 0.25
            if opens_inside and higher_closes and min(b1, b2, b3) > 0 and small_upper_wicks:
                matches.append(PatternMatch("three_white_soldiers", "BULLISH", 0.91))

        if all(self._candle(c)[3] < self._candle(c)[0] for c in (prev2, prev, last)):
            opens_inside = o2 >= c1 and o2 <= o1 and o3 >= c2 and o3 <= o2
            lower_closes = c2 < c1 and c3 < c2
            small_lower_wicks = (c1 - l1) <= r1 * 0.25 and (c2 - l2) <= r2 * 0.25 and (c3 - l3) <= r3 * 0.25
            if opens_inside and lower_closes and min(b1, b2, b3) > 0 and small_lower_wicks:
                matches.append(PatternMatch("three_black_crows", "BEARISH", 0.91))

        if len(ohlcv) >= 5:
            a, b, c, d, e = ohlcv[-5:]
            ao, ah, al, ac = self._candle(a)
            bo, bh, bl, bc = self._candle(b)
            co, ch, cl, cc = self._candle(c)
            do, dh, dl, dc = self._candle(d)
            eo, eh, el, ec = self._candle(e)
            ab = abs(ac - ao)
            eb = abs(ec - eo)
            ar = max(ah - al, 1e-12)
            er = max(eh - el, 1e-12)
            middle_inside = all(
                min(ao, ac) <= min(xo, xc) and max(xo, xc) <= max(ao, ac)
                for xo, xc in ((bo, bc), (co, cc), (do, dc))
            )
            if ac > ao and ab >= ar * 0.55 and middle_inside and eb >= er * 0.55 and ec > eo and ec > ah:
                matches.append(PatternMatch("rising_three_methods", "BULLISH", 0.84))
            if ac < ao and ab >= ar * 0.55 and middle_inside and eb >= er * 0.55 and ec < eo and ec < al:
                matches.append(PatternMatch("falling_three_methods", "BEARISH", 0.84))

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
