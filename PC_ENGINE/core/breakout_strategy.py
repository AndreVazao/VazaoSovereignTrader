from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .indicators import atr, vwap
from .preflight import validate_ohlcv_rows

Action = Literal["BUY", "SELL", "HOLD"]


@dataclass(frozen=True)
class BreakoutEvidence:
    action: Action
    score: float
    confidence: float
    breakout_pct: float
    volume_ratio: float
    reason: str


class BreakoutVolumeStrategy:
    """Breakout + relative-volume evidence; descriptive/PAPER only."""

    def __init__(self, settings: dict | None = None):
        cfg = settings or {}
        self.lookback = max(5, int(cfg.get("lookback", 20)))
        self.atr_period = max(2, int(cfg.get("atr_period", 14)))
        self.min_breakout = max(0.0, float(cfg.get("min_breakout_pct", 0.0015)))
        self.min_volume_ratio = max(1.0, float(cfg.get("min_volume_ratio", 1.25)))
        self.max_gap_seconds = cfg.get("max_gap_seconds")

    def analyse(self, ohlcv: list[list[float]]) -> BreakoutEvidence:
        if len(ohlcv) < max(self.lookback + 2, self.atr_period + 2):
            return BreakoutEvidence("HOLD", 0.0, 0.0, 0.0, 0.0, "warmup breakout")
        quality = validate_ohlcv_rows(ohlcv, max_gap_seconds=self.max_gap_seconds)
        if not quality.ok:
            return BreakoutEvidence("HOLD", 0.0, 0.0, 0.0, 0.0, "market data quality gate blocked breakout")
        current = ohlcv[-1]
        close = float(current[4])
        volume = float(current[5])
        previous = ohlcv[-self.lookback - 1:-1]
        highs = [float(c[2]) for c in previous]
        lows = [float(c[3]) for c in previous]
        avg_volume = sum(float(c[5]) for c in previous) / len(previous)
        a = atr(ohlcv, self.atr_period)
        if close <= 0 or avg_volume <= 0 or a is None:
            return BreakoutEvidence("HOLD", 0.0, 0.0, 0.0, 0.0, "indicadores insuficientes")
        high_break = (close - max(highs)) / close
        low_break = (close - min(lows)) / close
        breakout = high_break if high_break >= self.min_breakout else low_break if low_break <= -self.min_breakout else 0.0
        volume_ratio = volume / avg_volume
        if breakout == 0.0 or volume_ratio < self.min_volume_ratio:
            return BreakoutEvidence("HOLD", 0.0, 0.0, breakout, volume_ratio, "sem breakout confirmado por volume")
        atr_pct = a / close
        score = max(-1.0, min(1.0, breakout / max(0.01, atr_pct * 2)))
        action: Action = "BUY" if score > 0 else "SELL"
        confidence = min(1.0, 0.55 * min(1.0, abs(score)) + 0.45 * min(1.0, volume_ratio / 2.0))
        return BreakoutEvidence(action, round(score, 4), round(confidence, 4), round(breakout, 6), round(volume_ratio, 4), f"breakout={breakout:+.2%}, volume={volume_ratio:.2f}x")
