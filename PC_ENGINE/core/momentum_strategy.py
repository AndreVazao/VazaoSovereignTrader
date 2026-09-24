from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .indicators import atr, ema, pct_change
from .preflight import validate_ohlcv_rows

Action = Literal["BUY", "SELL", "HOLD"]

@dataclass(frozen=True)
class StrategyEvidence:
    action: Action
    score: float
    confidence: float
    reason: str

class MultiTimeframeMomentumStrategy:
    """Independent momentum evidence; never authorizes or executes orders."""
    def __init__(self, settings: dict | None = None):
        cfg = settings or {}
        self.fast_period = max(2, int(cfg.get("fast_ema", 8)))
        self.slow_period = max(self.fast_period + 1, int(cfg.get("slow_ema", 21)))
        self.min_alignment = max(1, int(cfg.get("min_aligned_timeframes", 2)))
        self.min_atr_pct = max(0.0, float(cfg.get("min_atr_pct", 0.0008)))
        self.weights = cfg.get("timeframe_weights", {"5m": 0.25, "15m": 0.30, "1h": 0.30, "4h": 0.15})
        self.max_gap_seconds = cfg.get("max_gap_seconds")

    def _frame_score(self, candles: list[list[float]]) -> float:
        if len(candles) < self.slow_period + 2:
            return 0.0
        quality = validate_ohlcv_rows(candles, max_gap_seconds=self.max_gap_seconds)
        if not quality.ok:
            return 0.0
        closes = [float(c[4]) for c in candles]
        fast, slow = ema(closes, self.fast_period), ema(closes, self.slow_period)
        a = atr(candles, min(14, max(2, len(candles) - 1)))
        price = closes[-1]
        if fast is None or slow is None or price <= 0 or a is None or a / price < self.min_atr_pct:
            return 0.0
        spread = (fast - slow) / price
        recent = pct_change(closes[-1], closes[-4]) if len(closes) >= 4 else 0.0
        return max(-1.0, min(1.0, spread * 120.0 + recent * 40.0))

    def analyse(self, timeframes: dict[str, list[list[float]]]) -> StrategyEvidence:
        scores = [(name, self._frame_score(candles), max(0.0, float(self.weights.get(name, 1.0)))) for name, candles in timeframes.items()]
        active = [(n, s, w) for n, s, w in scores if abs(s) >= 0.10]
        if not active:
            return StrategyEvidence("HOLD", 0.0, 0.0, "sem momentum suficiente")
        bullish = sum(1 for _, s, _ in active if s > 0)
        bearish = sum(1 for _, s, _ in active if s < 0)
        aligned = max(bullish, bearish)
        if aligned < self.min_alignment:
            return StrategyEvidence("HOLD", 0.0, aligned / max(1, len(active)), "timeframes sem alinhamento")
        total_weight = sum(w for _, _, w in active) or 1.0
        score = sum(s * w for _, s, w in active) / total_weight
        action: Action = "BUY" if score > 0.10 else "SELL" if score < -0.10 else "HOLD"
        confidence = min(1.0, 0.5 * abs(score) + 0.5 * aligned / max(1, len(active)))
        names = ", ".join(f"{n}:{s:+.2f}" for n, s, _ in active)
        return StrategyEvidence(action, round(score, 4), round(confidence, 4), f"momentum MTF [{names}]")
