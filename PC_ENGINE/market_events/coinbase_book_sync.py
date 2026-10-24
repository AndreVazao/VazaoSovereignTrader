from __future__ import annotations

import threading
import time
from math import isfinite
from dataclasses import dataclass
from typing import Callable

from .orderbook import OrderBookEvent, OrderBookLevel
from .orderbook_builder import OrderBookBuilder


@dataclass(frozen=True)
class CoinbaseBookView:
    venue: str
    symbol: str
    status: str
    sequence: int | None
    bids: tuple[OrderBookLevel, ...]
    asks: tuple[OrderBookLevel, ...]
    age_ms: float | None
    eligible: bool
    reason: str | None
    observation_time_ns: int | None = None


BookCallback = Callable[[CoinbaseBookView], None]


class CoinbaseL2BookSynchronizer:
    """Fail-closed Coinbase Advanced Trade L2 reconstruction.

    Coinbase supplies the initial snapshot through the level2 stream. A
    reconnect invalidates the previous book; a fresh stream snapshot is
    required before subsequent deltas can be accepted. This component only
    reconstructs/observes public data and never submits orders.
    """

    def __init__(
        self,
        symbol: str,
        on_book: BookCallback,
        *,
        max_age_ms: float = 1000.0,
    ) -> None:
        if not symbol or not isfinite(max_age_ms) or max_age_ms <= 0:
            raise ValueError("invalid_book_configuration")
        self.symbol = symbol
        self.on_book = on_book
        self.max_age_ms = float(max_age_ms)
        self._lock = threading.RLock()
        self._builder = OrderBookBuilder("coinbase", symbol)
        self._last_update_ns: int | None = None
        self._reason: str | None = "awaiting_snapshot"
        self._callback_errors = 0
        self._events_accepted = 0
        self._sequence_errors = 0

    def on_event(self, event: OrderBookEvent) -> None:
        if event.venue != "coinbase" or event.symbol != self.symbol:
            return
        with self._lock:
            rebuilt = self._builder.apply(event)
            if rebuilt is None:
                # Some builder rejection paths (for example an unsupported
                # event type) do not mutate the builder. Never retain its last
                # good depth after any untrusted event: require a new snapshot.
                self._builder = OrderBookBuilder("coinbase", self.symbol)
                self._last_update_ns = None
                self._reason = "invalid_sequence_or_book"
                self._sequence_errors += 1
            else:
                self._last_update_ns = event.local_receive_ns
                self._reason = None
                self._events_accepted += 1
            view = self._view_locked(event.local_receive_ns)
        self._emit(view)

    def invalidate(self, reason: str = "invalid_message") -> None:
        """Clear the last eligible view when an incoming depth message is untrustworthy."""
        with self._lock:
            self._builder = OrderBookBuilder("coinbase", self.symbol)
            self._last_update_ns = None
            self._reason = reason
            view = self._view_locked(0)
        self._emit(view)

    def connection_lost(self) -> None:
        self.invalidate("connection_lost")

    def snapshot(self, now_ns: int) -> CoinbaseBookView:
        """Re-evaluate freshness at read time, even if no new WS event arrives."""
        with self._lock:
            return self._view_locked(now_ns)

    def health(self, now_ns: int | None = None) -> dict[str, int | str | bool | float | None]:
        with self._lock:
            view = self._view_locked(now_ns if now_ns is not None else time.monotonic_ns())
            return {
                "venue": "coinbase",
                "symbol": self.symbol,
                "state": view.status,
                "sequence": view.sequence,
                "eligible": view.eligible,
                "age_ms": view.age_ms,
                "reason": view.reason,
                "events_accepted": self._events_accepted,
                "sequence_errors": self._sequence_errors,
                "callback_errors": self._callback_errors,
            }

    def _view_locked(self, now_ns: int) -> CoinbaseBookView:
        book = self._builder.snapshot()
        clock_regressed = (
            self._last_update_ns is not None and now_ns < self._last_update_ns
        )
        age_ms = (
            None if self._last_update_ns is None or clock_regressed
            else (now_ns - self._last_update_ns) / 1_000_000
        )
        fresh = age_ms is not None and age_ms <= self.max_age_ms
        crossed = bool(book.bids and book.asks) and book.best_bid >= book.best_ask
        has_sides = bool(book.bids) and bool(book.asks)
        eligible = (
            self._builder.initialized and fresh and has_sides and not crossed
            and not clock_regressed
        )
        reason = self._reason
        if reason is None:
            if clock_regressed:
                reason = "clock_regression"
            elif not fresh:
                reason = "stale"
            elif not has_sides:
                reason = "empty_side"
            elif crossed:
                reason = "crossed_book"
        return CoinbaseBookView(
            venue="coinbase",
            symbol=self.symbol,
            status="SYNCED" if self._builder.initialized else "INVALID",
            sequence=book.sequence,
            bids=book.bids,
            asks=book.asks,
            age_ms=age_ms,
            eligible=eligible,
            reason=reason,
            observation_time_ns=self._last_update_ns,
        )

    def _emit(self, view: CoinbaseBookView) -> None:
        try:
            self.on_book(view)
        except Exception:
            with self._lock:
                self._callback_errors += 1
