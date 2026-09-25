from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


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


def _candle(row: list[float]) -> tuple[float, float, float, float] | None:
    if len(row) < 5:
        return None
    try:
        o, h, l, c = (float(row[1]), float(row[2]), float(row[3]), float(row[4]))
    except (TypeError, ValueError):
        return None
    if not all(isfinite(v) for v in (o, h, l, c)) or min(o, h, l, c) <= 0 or h < max(o, c) or l > min(o, c) or h <= l:
        return None
    return o, h, l, c


def _parts(row: list[float]) -> tuple[float, float, float, float, float] | None:
    c = _candle(row)
    if c is None:
        return None
    o, h, l, close = c
    body = abs(close - o)
    rng = h - l
    upper = h - max(o, close)
    lower = min(o, close) - l
    return body, rng, upper, lower, close - o


def _trend(rows: list[list[float]], lookback: int = 5) -> int:
    closes = []
    for row in rows[-(lookback + 1):]:
        c = _candle(row)
        if c:
            closes.append(c[3])
    if len(closes) < 3:
        return 0
    delta = closes[-1] - closes[0]
    threshold = max(closes[0] * 0.001, 1e-12)
    return 1 if delta > threshold else -1 if delta < -threshold else 0


def detect_candlestick_patterns(rows: list[list[float]]) -> list[CandlestickPattern]:
    valid = [row for row in rows if _parts(row) is not None]
    if not valid:
        return []
    out: list[CandlestickPattern] = []
    i = len(valid) - 1
    p0 = _parts(valid[-1])
    assert p0 is not None
    body, rng, upper, lower, signed = p0
    bullish = signed > 0
    bearish = signed < 0
    tiny = body <= rng * 0.10
    trend = _trend(valid[:-1] if len(valid) > 1 else valid)

    if tiny and lower >= rng * 0.60 and upper <= rng * 0.15:
        out.append(CandlestickPattern("dragonfly_doji", "BUY", 0.62, 0.72, i))
    if tiny and upper >= rng * 0.60 and lower <= rng * 0.15:
        out.append(CandlestickPattern("gravestone_doji", "SELL", -0.62, 0.72, i))
    if lower >= max(body * 2.0, rng * 0.50) and upper <= rng * 0.20:
        name = "hammer" if trend <= 0 else "hanging_man"
        direction = "BUY" if trend <= 0 else "SELL"
        score = 0.72 if direction == "BUY" else -0.68
        out.append(CandlestickPattern(name, direction, score, 0.76, i))
    if upper >= max(body * 2.0, rng * 0.50) and lower <= rng * 0.20:
        name = "inverted_hammer" if trend <= 0 else "shooting_star"
        direction = "BUY" if trend <= 0 else "SELL"
        score = 0.58 if direction == "BUY" else -0.72
        out.append(CandlestickPattern(name, direction, score, 0.72, i))

    if len(valid) >= 2:
        prev = _parts(valid[-2])
        assert prev is not None
        pb, pr, pu, pl, ps = prev
        po, ph, p_low, pc = _candle(valid[-2])  # type: ignore[misc]
        co, ch, cl, cc = _candle(valid[-1])  # type: ignore[misc]
        if bearish and bullish and False:
            pass
        if ps < 0 and signed > 0 and co <= pc and cc >= po and body >= pb * 0.9:
            out.append(CandlestickPattern("bullish_engulfing", "BUY", 0.86, 0.84, i))
        if ps > 0 and signed < 0 and co >= pc and cc <= po and body >= pb * 0.9:
            out.append(CandlestickPattern("bearish_engulfing", "SELL", -0.86, 0.84, i))
        prev_mid = (po + pc) / 2.0
        if ps < 0 and signed > 0 and cc > prev_mid and cc < po:
            out.append(CandlestickPattern("piercing_line", "BUY", 0.68, 0.72, i))
        if ps > 0 and signed < 0 and cc < prev_mid and cc > po:
            out.append(CandlestickPattern("dark_cloud_cover", "SELL", -0.68, 0.72, i))
        if pb > 0 and body <= pb * 0.65 and min(po, pc) <= min(co, cc) <= max(po, pc) and min(po, pc) <= min(co, cc) and max(co, cc) <= max(po, pc):
            out.append(CandlestickPattern("bullish_harami" if signed > 0 else "bearish_harami", "BUY" if signed > 0 else "SELL", 0.64 if signed > 0 else -0.64, 0.70, i))
        if ps < 0 and signed > 0 and cc > pc:
            out.append(CandlestickPattern("three_inside_up_candidate", "BUY", 0.52, 0.60, i))
        if ps > 0 and signed < 0 and cc < pc:
            out.append(CandlestickPattern("three_inside_down_candidate", "SELL", -0.52, 0.60, i))

    if len(valid) >= 3:
        a, b, c = valid[-3:]
        pa, pb, pc = _parts(a), _parts(b), _parts(c)
        ca, cb, cc = _candle(a), _candle(b), _candle(c)
        if pa and pb and pc and ca and cb and cc:
            ab, ar, au, al, ass = pa
            bb, br, bu, bl, bss = pb
            cbod, cr, cu, cl, css = pc
            if ass < 0 and css > 0 and bb <= ar * 0.45 and cbod >= ab * 0.55 and cc[3] > (ca[0] + ca[3]) / 2:
                out.append(CandlestickPattern("morning_star", "BUY", 0.82, 0.78, i))
            if ass > 0 and css < 0 and bb <= ar * 0.45 and cbod >= ab * 0.55 and cc[3] < (ca[0] + ca[3]) / 2:
                out.append(CandlestickPattern("evening_star", "SELL", -0.82, 0.78, i))
            if ass < 0 and bss > 0 and css > 0:
                out.append(CandlestickPattern("three_white_soldiers_candidate", "BUY", 0.70, 0.66, i))
            if ass > 0 and bss < 0 and css < 0:
                out.append(CandlestickPattern("three_black_crows_candidate", "SELL", -0.70, 0.66, i))
            if ass < 0 and bss > 0 and css > 0 and cb[0] > ca[2] and cc[0] > cb[2]:
                out.append(CandlestickPattern("three_outside_up_candidate", "BUY", 0.76, 0.70, i))
            if ass > 0 and bss < 0 and css < 0 and cb[0] < ca[1] and cc[0] < cb[1]:
                out.append(CandlestickPattern("three_outside_down_candidate", "SELL", -0.76, 0.70, i))

    return out


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
    confidence = min(1.0, 0.45 * dominant.confidence + 0.55 * min(1.0, len(patterns) / 3.0))
    return CandlestickEvidence(round(max(-1.0, min(1.0, total)), 4), round(confidence, 4), dominant.name, tuple(patterns))
