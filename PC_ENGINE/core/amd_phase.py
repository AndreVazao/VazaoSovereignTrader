from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class AMDPhaseEvidence:
    phase: str
    direction: str
    score: float
    confidence: float
    range_high: float
    range_low: float
    sweep: str
    displacement: float
    paper_only: bool = True


def _ohlc(row):
    if len(row) < 5:
        return None
    try:
        o, h, l, c = map(float, row[1:5])
    except (TypeError, ValueError):
        return None
    if not all(isfinite(v) for v in (o, h, l, c)) or min(o, h, l, c) <= 0 or h <= l:
        return None
    return o, h, l, c


def analyze_amd(rows: list[list[float]], lookback: int = 20) -> AMDPhaseEvidence:
    candles = [x for x in (_ohlc(r) for r in rows) if x is not None]
    if len(candles) < max(8, lookback // 2):
        return AMDPhaseEvidence("UNKNOWN", "NEUTRAL", 0.0, 0.0, 0.0, 0.0, "NONE", 0.0)
    window = candles[-(lookback + 1):-1]
    last = candles[-1]
    hi = max(x[1] for x in window)
    lo = min(x[2] for x in window)
    width = max(hi - lo, 1e-12)
    o, h, l, c = last
    sweep = "NONE"
    if h > hi and c < hi:
        sweep = "HIGH"
    elif l < lo and c > lo:
        sweep = "LOW"
    displacement = (c - o) / max(width, c * 1e-9)
    compression = sum((x[1] - x[2]) for x in window[-6:]) / max(1, len(window[-6:]))
    baseline = sum((x[1] - x[2]) for x in window[:-6]) / max(1, len(window[:-6]))
    compression_ratio = compression / max(baseline, 1e-12)

    if compression_ratio < 0.70 and sweep == "NONE":
        phase, direction, score, confidence = "ACCUMULATION", "NEUTRAL", 0.0, min(0.85, 0.55 + (0.70 - compression_ratio))
    elif sweep == "LOW" and displacement > 0.15:
        phase, direction, score, confidence = "MANIPULATION", "BUY", min(1.0, 0.55 + displacement), min(0.90, 0.60 + abs(displacement))
    elif sweep == "HIGH" and displacement < -0.15:
        phase, direction, score, confidence = "MANIPULATION", "SELL", max(-1.0, -0.55 - abs(displacement)), min(0.90, 0.60 + abs(displacement))
    elif abs(displacement) > 0.30:
        phase = "DISTRIBUTION" if displacement < 0 else "EXPANSION"
        direction = "SELL" if displacement < 0 else "BUY"
        score, confidence = max(-1.0, min(1.0, displacement)), min(0.90, 0.55 + abs(displacement))
    else:
        phase, direction, score, confidence = "TRANSITION", "NEUTRAL", 0.0, 0.35

    return AMDPhaseEvidence(phase, direction, round(score, 4), round(confidence, 4), hi, lo, sweep, round(displacement, 4))
