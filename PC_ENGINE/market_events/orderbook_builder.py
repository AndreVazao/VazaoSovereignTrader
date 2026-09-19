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
    """Sequence-aware L2 book builder.

    A book is executable only after a valid snapshot/bootstrap. For venues
    exposing range sequences (e.g. Binance U/u), callers can bootstrap from a
    REST snapshot plus buffered WebSocket deltas. Once live, a gap or backwards
    sequence marks the book stale and requires another bootstrap.
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
            self._load_snapshot(event)
            return self.snapshot()
        if event.event_type != "delta" or not self.initialized:
            return None
        if not self._sequence_is_contiguous(event):
            self.stale = True
            return None
        self._apply_levels(self._bids, event.bids)
        self._apply_levels(self._asks, event.asks)
        self._sequence = event.sequence if event.sequence is not None else self._sequence
        return self.snapshot()

    def bootstrap(self, snapshot: OrderBookEvent, buffered_deltas: list[OrderBookEvent]) -> ReconstructedBook | None:
        """Load a snapshot and replay only deltas that safely bridge it.

        For Binance, the snapshot sequence is lastUpdateId and buffered events
        carry U/u via sequence_start/sequence. For venues with a single
        monotonic sequence, sequence_start may be None and +1 continuity is
        enforced.
        """
        if snapshot.venue != self.venue or snapshot.symbol != self.symbol:
            return None
        if snapshot.event_type != "snapshot":
            return None
        self._load_snapshot(snapshot)
        ordered = sorted(
            (event for event in buffered_deltas if event.venue == self.venue and event.symbol == self.symbol),
            key=lambda event: event.sequence if event.sequence is not None else -1,
        )
        bridged = False
        for event in ordered:
            if event.sequence is None:
                continue
            if event.sequence <= (self._sequence or -1):
                continue
            if event.sequence_start is not None:
                if not (event.sequence_start <= (self._sequence or 0) + 1 <= event.sequence):
                    continue
            else:
                if event.sequence != (self._sequence or 0) + 1:
                    self.stale = True
                    return None
            self._apply_levels(self._bids, event.bids)
            self._apply_levels(self._asks, event.asks)
            self._sequence = event.sequence
            bridged = True
        if buffered_deltas and not bridged:
            self.stale = True
            return None
        return self.snapshot()

    def _load_snapshot(self, event: OrderBookEvent) -> None:
        self._bids = {level.price: level.quantity for level in event.bids if level.quantity > 0}
        self._asks = {level.price: level.quantity for level in event.asks if level.quantity > 0}
        self._sequence = event.sequence
        self._initialized = True
        self.stale = False

    def _sequence_is_contiguous(self, event: OrderBookEvent) -> bool:
        if event.sequence is None or self._sequence is None:
            return True
        if event.sequence <= self._sequence:
            return False
        if event.sequence_start is not None:
            return event.sequence_start <= self._sequence + 1 <= event.sequence
        return event.sequence == self._sequence + 1

    @staticmethod
    def _apply_levels(book: dict[float, float], levels: tuple[OrderBookLevel, ...]) -> None:
        for level in levels:
            if level.quantity <= 0:
                book.pop(level.price, None)
            else:
                book[level.price] = level.quantity

    def snapshot(self) -> ReconstructedBook:
        bids = tuple(OrderBookLevel(price, qty) for price, qty in sorted(self._bids.items(), reverse=True))
        asks = tuple(OrderBookLevel(price, qty) for price, qty in sorted(self._asks.items()))
        return ReconstructedBook(
            venue=self.venue,
            symbol=self.symbol,
            sequence=self._sequence,
            bids=bids,
            asks=asks,
        )
