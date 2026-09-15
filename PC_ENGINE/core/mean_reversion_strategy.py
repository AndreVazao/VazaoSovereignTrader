from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .indicators import atr, ema, vwap

Action = Literal["BUY", "SELL", "HOLD"]

@dataclass(frozen=True)
class StrategyEvidence:
    action: Action
    score: float
    confidence: float
    reason: str

class MeanReversionStrategy:
    """Mean-reversion evidence for ranging markets; never executes orders."""
    def __init__(self, settings: dict | None = None):
        cfg = settings or {}
        self.vwap_period = max(2, int(cfg.get("vwap_period", 30)))
        self.atr_period = max(2, int(cfg.get("atr_period", 14)))
        self.min_deviation = max(0.0, float(cfg.get("min_deviation_pct", 0.0025)))
        self.max_deviation = max(self.min_deviation, float(cfg.get("max_deviation_pct", 0.025)))
        self.min_atr_pct = max(0.0, float(cfg.get("min_atr_pct", 0.001)))
        self.max_atr_pct = max(self.min_atr_pct, float(cfg.get("max_atr_pct", 0.012)))

    def analyse(self, ohlcv: list[list[float]], regime: str | None = None) -> StrategyEvidence:
        if len(ohlcv) < max(self.vwap_period, self.atr_period) + 2:
            return StrategyEvidence("HOLD", 0.0, 0.0, "warmup mean reversion")
        if regime and regime not in {"RANGE", "LOW_VOL", "FLAT", "NORMAL"}:
            return StrategyEvidence("HOLD", 0.0, 0.0, f"regime {regime} desfavorável à reversão")
        price = float(ohlcv[-1][4])
        vw = vwap(ohlcv, self.vwap_period)
        a = atr(ohlcv, self.atr_period)
        if price <= 0 or vw is None or a is None:
            return StrategyEvidence("HOLD", 0.0, 0.0, "indicadores insuficientes")
        atr_pct = a / price
        deviation = (price - vw) / vw if vw else 0.0
        if atr_pct < self.min_atr_pct or atr_pct > self.max_atr_pct:
            return StrategyEvidence("HOLD", 0.0, 0.0, "volatilidade fora da faixa")
        if abs(deviation) < self.min_deviation or abs(deviation) > self.max_deviation:
            return StrategyEvidence("HOLD", 0.0, 0.0, "desvio da média insuficiente/excessivo")
        raw = max(-1.0, min(1.0, -deviation / self.max_deviation))
        action: Action = "BUY" if raw > 0.10 else "SELL" if raw < -0.10 else "HOLD"
        confidence = min(1.0, abs(raw) * 0.7 + 0.3)
        return StrategyEvidence(action, round(raw, 4), round(confidence, 4), f"mean reversion: preço {deviation:+.2%} vs VWAP")
