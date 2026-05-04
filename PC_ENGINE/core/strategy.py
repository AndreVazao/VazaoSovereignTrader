from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .indicators import atr, ema, slope, vwap

Action = Literal["BUY", "SELL", "HOLD"]
Regime = Literal["TREND_UP", "TREND_DOWN", "RANGE", "CHAOS", "WARMUP"]


@dataclass
class Signal:
    action: Action
    regime: Regime
    strength: float
    reason: str
    stop_pct: float
    take_profit_pct: float


class TrendEmaAtrStrategy:
    def __init__(self, settings: dict):
        self.settings = settings
        self.last_ema_long: dict[str, float] = {}

    def analyse(self, symbol: str, ohlcv: list[list[float]], spread_pct: float = 0.0) -> Signal:
        cfg = self.settings
        closes = [float(c[4]) for c in ohlcv]
        price = closes[-1] if closes else 0.0
        if len(closes) < max(cfg["ema_long"], cfg["atr_period"], cfg["vwap_period"]) + 2:
            return Signal("HOLD", "WARMUP", 0.0, "warmup", 0.0, 0.0)

        ema_s = ema(closes, int(cfg["ema_short"]))
        ema_l = ema(closes, int(cfg["ema_long"]))
        previous_ema_l = self.last_ema_long.get(symbol)
        self.last_ema_long[symbol] = ema_l or 0.0
        a = atr(ohlcv, int(cfg["atr_period"]))
        vw = vwap(ohlcv, int(cfg["vwap_period"]))

        if ema_s is None or ema_l is None or a is None or vw is None or price <= 0:
            return Signal("HOLD", "WARMUP", 0.0, "not enough indicator data", 0.0, 0.0)

        atr_pct = a / price
        slp = slope(ema_l, previous_ema_l)
        if spread_pct > float(cfg["spread_max_pct"]):
            return Signal("HOLD", "CHAOS", 0.0, "spread too wide", 0.0, 0.0)
        if atr_pct < float(cfg["atr_pct_min"]):
            return Signal("HOLD", "RANGE", 0.0, "atr too low", 0.0, 0.0)

        slope_th = float(cfg["slope_threshold"])
        if abs(slp) < slope_th:
            return Signal("HOLD", "RANGE", 0.0, "slope too weak", 0.0, 0.0)

        stop_pct = atr_pct * float(cfg["stop_atr_mult"])
        tp_pct = atr_pct * float(cfg["take_profit_atr_mult"])
        trend_strength = min(1.0, max(0.0, abs(slp) / (slope_th * 4)))
        volatility_quality = min(1.0, max(0.0, atr_pct / (float(cfg["atr_pct_min"]) * 4)))
        strength = round((trend_strength * 0.65) + (volatility_quality * 0.35), 4)

        if slp > 0 and ema_s > ema_l and price >= vw:
            return Signal("BUY", "TREND_UP", strength, "trend up + price above vwap", stop_pct, tp_pct)
        if ema_s < ema_l or slp < -slope_th:
            return Signal("SELL", "TREND_DOWN", strength, "trend weakened", stop_pct, tp_pct)
        return Signal("HOLD", "RANGE", strength, "conditions incomplete", stop_pct, tp_pct)
