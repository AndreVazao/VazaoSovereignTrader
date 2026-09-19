from __future__ import annotations

from dataclasses import dataclass
from random import Random


@dataclass(frozen=True)
class BookLevel:
    price: float
    quantity: float


@dataclass(frozen=True)
class OrderBookSnapshot:
    venue: str
    symbol: str
    timestamp_ms: float
    bids: tuple[BookLevel, ...]
    asks: tuple[BookLevel, ...]

    @property
    def best_bid(self) -> float | None:
        return self.bids[0].price if self.bids else None

    @property
    def best_ask(self) -> float | None:
        return self.asks[0].price if self.asks else None

    @property
    def spread_bps(self) -> float | None:
        if not self.best_bid or not self.best_ask:
            return None
        mid = (self.best_bid + self.best_ask) / 2.0
        return (self.best_ask - self.best_bid) / mid * 10_000.0


@dataclass(frozen=True)
class FillSimulation:
    status: str
    requested_qty: float
    filled_qty: float
    average_price: float | None
    notional: float
    consumed_levels: int
    liquidity_limited: bool
    rejected: bool
    reason: str


class OrderBookSimulator:
    """Conservative PAPER-only book-depth fill simulator."""

    def __init__(self, *, rejection_probability: float = 0.0, seed: int = 0) -> None:
        self.rejection_probability = min(1.0, max(0.0, rejection_probability))
        self.random = Random(seed)

    def simulate_market_order(
        self,
        book: OrderBookSnapshot,
        *,
        side: str,
        quantity: float,
    ) -> FillSimulation:
        side = side.upper()
        if quantity <= 0:
            return FillSimulation("INVALID", quantity, 0.0, None, 0.0, 0, False, True, "invalid_quantity")
        if side not in {"BUY", "SELL"}:
            return FillSimulation("INVALID", quantity, 0.0, None, 0.0, 0, False, True, "invalid_side")
        if self.random.random() < self.rejection_probability:
            return FillSimulation("REJECTED", quantity, 0.0, None, 0.0, 0, False, True, "simulated_rejection")

        levels = book.asks if side == "BUY" else book.bids
        remaining = quantity
        filled = 0.0
        notional = 0.0
        consumed = 0

        for level in levels:
            if remaining <= 0:
                break
            if level.price <= 0 or level.quantity <= 0:
                continue
            take = min(remaining, level.quantity)
            filled += take
            notional += take * level.price
            remaining -= take
            consumed += 1

        if filled <= 0:
            return FillSimulation("NO_LIQUIDITY", quantity, 0.0, None, 0.0, consumed, True, False, "empty_book")

        average = notional / filled
        if remaining > 0:
            return FillSimulation("PARTIAL", quantity, filled, average, notional, consumed, True, False, "insufficient_depth")
        return FillSimulation("FILLED", quantity, filled, average, notional, consumed, False, False, "ok")
