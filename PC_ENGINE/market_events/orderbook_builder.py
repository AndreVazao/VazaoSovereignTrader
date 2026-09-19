from __future__ import annotations

from dataclasses import dataclass

from .orderbook import OrderBookEvent, OrderBookLevel


@dataclass(frozen=True)
class ReconstructedBook:
    venue: str
    symbol: str
    sequence: int | None
    bids: tuple[OrderBookLevel, ...]
    asks: tuple[OrderBookLevel, ...]

    @property
    def best_bid(self) -> float | None:
        return self.bids[0].price if self.bids else None

    @property
    def best_ask(self) -> float | None:
        return self.asks[0].price if self.asks else None


class OrderBookBuilder:
    """Deterministic snapshot/delta builder for normalized L2 events.

    Deltas are rejected until a snapshot has initialized the book. When
    sequence numbers are present, a backwards or skipped sequence marks the
    builder stale and requires a new snapshot.
    """

    def __init__(self, venue: str, symbol: str) -> None:
        self.venue = venue
        self.symbol = symbol
        self._bids: dict[float, float] = {}
        self._asks: dict[float, float] = {}
        self._sequence: int | None = None
        self._initialized = False
        self.stale = True

    @property
    def initialized(self) -> bool:
        return self._initialized and not self.stale

    def apply(self, event: OrderBookEvent) -> ReconstructedBook | None:
        if event.venue != self.venue or event.symbol != self.symbol:
            return None

        if event.event_type == "snapshot":
            self._bids = {level.price: level.quantity for level in event.bids if level.quantity > 0}
            self._asks = {level.price: level.quantity for level in event.asks if level.quantity > 0}
            self._sequence = event.sequence
            self._initialized = True
            self.stale = False
            return self.snapshot()

        if event.event_type != "delta":
            return None
        if not self._initialized or self.stale:
            return None
        if event.sequence is not None and self._sequence is not None and event.sequence <= self._sequence:
            self.stale = True
            return None

        self._apply_levels(self._bids, event.bids)
        self._apply_levels(self._asks, event.asks)
        self._sequence = event.sequence if event.sequence is not None else self._sequence
        return self.snapshot()

    @staticmethod
    def _apply_levels(book: dict[float, float], levels: tuple[OrderBookLevel, ...]) -> None:
        for level in levels:
            if level.quantity <= 0:
                book.pop(level.price, None)
            else:
                book[level.price] = level.quantity

    def snapshot(self) -> ReconstructedBook:
        bids = tuple(
            OrderBookLevel(price, qty)
            for price, qty in sorted(self._bids.items(), reverse=True)
        )
        asks = tuple(
            OrderBookLevel(price, qty)
            for price, qty in sorted(self._asks.items())
        )
        return ReconstructedBook(
            venue=self.venue,
            symbol=self.symbol,
            sequence=self._sequence,
            bids=bids,
            asks=asks,
        )
