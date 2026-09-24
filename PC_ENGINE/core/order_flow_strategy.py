from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Literal

Action = Literal["BUY", "SELL", "HOLD"]


@dataclass(frozen=True)
class OrderFlowEvidence:
    action: Action
    score: float
    confidence: float
    buy_volume: float
    sell_volume: float
    imbalance: float
    trades: int
    reason: str


class OrderFlowStrategy:
    """Trade-flow evidence derived from public WebSocket trade events.

    Observation/evidence only. It never submits orders and should be used by
    the confluence layer together with independent market evidence.
    """

    def __init__(self, settings: dict | None = None):
        cfg = settings or {}
        self.min_trades = max(1, int(cfg.get("min_trades", 30)))
        self.min_imbalance = min(0.95, max(0.0, float(cfg.get("min_imbalance", 0.12))))
        self.max_imbalance = min(1.0, max(self.min_imbalance, float(cfg.get("max_imbalance", 0.85))))
        self.min_notional = max(0.0, float(cfg.get("min_notional", 0.0)))
        self.max_event_age_ms = max(0, int(cfg.get("max_event_age_ms", 0)))

    def analyse(self, events: list[dict]) -> OrderFlowEvidence:
        buy = 0.0
        sell = 0.0
        trades = 0
        for event in events:
            try:
                price = float(event.get("price", 0.0))
                quantity = float(event.get("quantity", 0.0))
                side = str(event.get("side", "")).upper()
            except (TypeError, ValueError):
                continue
            if not math.isfinite(price) or not math.isfinite(quantity):
                continue
            if price <= 0 or quantity <= 0 or price * quantity < self.min_notional:
                continue
            if side == "BUY":
                buy += price * quantity
            elif side == "SELL":
                sell += price * quantity
            else:
                continue
            trades += 1

        total = buy + sell
        if trades < self.min_trades or total <= 0:
            return OrderFlowEvidence("HOLD", 0.0, 0.0, buy, sell, 0.0, trades, "order flow insuficiente")

        imbalance = (buy - sell) / total
        if abs(imbalance) < self.min_imbalance:
            return OrderFlowEvidence("HOLD", 0.0, 0.0, buy, sell, imbalance, trades, "imbalance abaixo do mínimo")

        # max_imbalance is a score saturation point, not a rejection boundary:
        # an extreme imbalance is stronger evidence, not invalid evidence.
        score = max(-1.0, min(1.0, imbalance / self.max_imbalance))
        action: Action = "BUY" if score >= self.min_imbalance / self.max_imbalance else "SELL" if score <= -self.min_imbalance / self.max_imbalance else "HOLD"
        confidence = min(1.0, 0.5 * abs(score) + 0.5 * min(1.0, trades / (self.min_trades * 4)))
        return OrderFlowEvidence(action, round(score, 4), round(confidence, 4), buy, sell, round(imbalance, 4), trades, f"order flow imbalance={imbalance:+.2%}")
