from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite

from .orderbook import OrderBookEvent, OrderBookLevel


class BookStatus(str, Enum):
    UNINITIALIZED = "UNINITIALIZED"
    SYNCED = "SYNCED"
    INVALID = "INVALID"


@dataclass(frozen=True)
class BookSnapshot:
    status: BookStatus
    update_id: int | None
    bids: tuple[OrderBookLevel, ...]
    asks: tuple[OrderBookLevel, ...]
    age_ms: float | None
    eligible: bool
    reason: str | None


class BinanceSpotDepthBook:
    """Fail-closed state for Binance Spot diff-depth updates.

    The caller owns WebSocket buffering and REST snapshot retrieval. This
    class never performs network I/O and never submits orders.
    """

    def __init__(self, symbol: str, max_age_ms: float = 1000.0, max_levels: int = 5000):
        if not symbol or not isfinite(max_age_ms) or max_age_ms <= 0 or max_levels < 1:
            raise ValueError("invalid book configuration")
        self.symbol = symbol
        self.max_age_ms = max_age_ms
        self.max_levels = max_levels
        self.status = BookStatus.UNINITIALIZED
        self.update_id: int | None = None
        self.last_update_ns: int | None = None
        self.bids: dict[float, float] = {}
        self.asks: dict[float, float] = {}
        self.reason: str | None = "awaiting_snapshot"

    @staticmethod
    def _levels(levels: tuple[OrderBookLevel, ...], snapshot: bool) -> dict[float, float]:
        result: dict[float, float] = {}
        for level in levels:
            price, qty = float(level.price), float(level.quantity)
            if not isfinite(price) or price <= 0 or not isfinite(qty) or qty < 0:
                raise ValueError("invalid_level")
            if snapshot and qty == 0:
                raise ValueError("zero_snapshot_quantity")
            if qty == 0:
                result.pop(price, None)
            else:
                result[price] = qty
        return result

    def invalidate(self, reason: str) -> None:
        self.status = BookStatus.INVALID
        self.reason = reason
        self.update_id = None
        self.last_update_ns = None
        self.bids.clear()
        self.asks.clear()

    def install_snapshot(self, update_id: int, bids: tuple[OrderBookLevel, ...],
                         asks: tuple[OrderBookLevel, ...]) -> bool:
        if not isinstance(update_id, int) or isinstance(update_id, bool) or update_id < 0:
            self.invalidate("invalid_snapshot_id")
            return False
        try:
            self.bids = self._levels(bids, snapshot=True)
            self.asks = self._levels(asks, snapshot=True)
        except (TypeError, ValueError, OverflowError):
            self.invalidate("invalid_snapshot_levels")
            return False
        self.update_id = update_id
        self.last_update_ns = None
        self.status = BookStatus.UNINITIALIZED
        self.reason = "awaiting_contiguous_delta"
        self._trim()
        return True

    def apply_delta(self, event: OrderBookEvent) -> bool:
        if event.venue != "binance" or event.symbol != self.symbol or event.event_type != "delta":
            self.invalidate("unexpected_event")
            return False
        if event.sequence is None or event.sequence_start is None or self.update_id is None:
            self.invalidate("missing_sequence_or_snapshot")
            return False
        if self.status == BookStatus.INVALID:
            return False
        start, end = event.sequence_start, event.sequence
        if (
            not isinstance(start, int) or isinstance(start, bool)
            or not isinstance(end, int) or isinstance(end, bool)
            or start < 0 or end < 0 or start > end
        ):
            self.invalidate("invalid_sequence_range")
            return False
        if end <= self.update_id:
            return False
        if start > self.update_id + 1:
            self.invalidate("sequence_gap")
            return False
        if not (start <= self.update_id + 1 <= end):
            self.invalidate("sequence_not_contiguous")
            return False
        try:
            bid_updates = self._levels(event.bids, snapshot=False)
            ask_updates = self._levels(event.asks, snapshot=False)
        except (TypeError, ValueError, OverflowError):
            self.invalidate("invalid_delta_levels")
            return False
        for level in event.bids:
            if level.quantity == 0:
                self.bids.pop(level.price, None)
        for price, qty in bid_updates.items():
            self.bids[price] = qty
        for level in event.asks:
            if level.quantity == 0:
                self.asks.pop(level.price, None)
        for price, qty in ask_updates.items():
            self.asks[price] = qty
        self._trim()
        self.update_id = end
        self.last_update_ns = event.local_receive_ns
        self.status = BookStatus.SYNCED
        self.reason = None
        return True

    def _trim(self) -> None:
        self.bids = dict(sorted(self.bids.items(), reverse=True)[:self.max_levels])
        self.asks = dict(sorted(self.asks.items())[:self.max_levels])

    def snapshot(self, now_ns: int) -> BookSnapshot:
        age_ms = None if self.last_update_ns is None else max(0, now_ns - self.last_update_ns) / 1_000_000
        fresh = age_ms is not None and age_ms <= self.max_age_ms
        crossed = bool(self.bids and self.asks) and max(self.bids) >= min(self.asks)
        eligible = (
            self.status == BookStatus.SYNCED and fresh and bool(self.bids)
            and bool(self.asks) and not crossed
        )
        reason = self.reason if self.reason else (
            "stale" if not fresh else "crossed_book" if crossed else None
        )
        return BookSnapshot(
            self.status, self.update_id,
            tuple(OrderBookLevel(p, q) for p, q in sorted(self.bids.items(), reverse=True)),
            tuple(OrderBookLevel(p, q) for p, q in sorted(self.asks.items())),
            age_ms, eligible, reason,
        )
