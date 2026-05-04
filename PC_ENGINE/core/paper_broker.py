from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass
class PaperFill:
    side: str
    symbol: str
    qty: float
    requested_price: float
    fill_price: float
    fee: float
    slippage_pct: float


class PaperBroker:
    def __init__(self, fee_pct: float = 0.001, slippage_pct: float = 0.0005, reject_probability: float = 0.0):
        self.fee_pct = fee_pct
        self.slippage_pct = slippage_pct
        self.reject_probability = reject_probability

    def fill(self, symbol: str, side: str, qty: float, price: float, spread_pct: float = 0.0) -> PaperFill:
        if random.random() < self.reject_probability:
            raise RuntimeError("paper simulated rejection")
        direction = 1 if side.lower() == "buy" else -1
        slip = max(self.slippage_pct, spread_pct / 2)
        fill_price = price * (1 + direction * slip)
        fee = abs(qty * fill_price * self.fee_pct)
        return PaperFill(
            side=side,
            symbol=symbol,
            qty=qty,
            requested_price=price,
            fill_price=fill_price,
            fee=fee,
            slippage_pct=slip,
        )
