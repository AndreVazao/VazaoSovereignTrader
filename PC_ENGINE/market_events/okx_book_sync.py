from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from math import isfinite
from typing import Callable

from .orderbook import OrderBookEvent, OrderBookLevel
from .orderbook_builder import OrderBookBuilder


@dataclass(frozen=True)
class OKXBookView:
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


BookCallback = Callable[[OKXBookView], None]


class OKXBooksSynchronizer:
    """Fail-closed reconstruction for the OKX incremental `books` channel.

    This expects parser-normalized snapshot/delta events. A delta's
    sequence_start is prevSeqId + 1, so it must equal the current sequence + 1;
    Binance's U/u overlap rule is deliberately not reused. This component
    observes public data only and never submits orders.
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
        self._builder = OrderBookBuilder("okx", symbol)
        self._last_update_ns: int | None = None
        self._reason: str | None = "awaiting_snapshot"
        self._events_accepted = 0
        self._sequence_errors = 0
        self._callback_errors = 0

    def on_event(self, event: OrderBookEvent) -> None:
        if event.venue != "okx" or event.symbol != self.symbol:
            return
        with self._lock:
            reason = None
            if event.event_type == "delta":
                current = self._builder.snapshot().sequence
                if (
                    not self._builder.initialized
                    or current is None
                    or event.sequence_start is None
                    or event.sequence_start != current + 1
                    or event.sequence is None
                    or event.sequence <= current
                ):
                    self._reset_locked("sequence_gap")
                    self._sequence_errors += 1
                    view = self._view_locked(event.local_receive_ns)
                    reason = "sequence_gap"
                else:
                    rebuilt = self._builder.apply(event)
                    if rebuilt is None:
                        self._reset_locked("invalid_sequence_or_book")
                        self._sequence_errors += 1
                        view = self._view_locked(event.local_receive_ns)
                    else:
                        self._last_update_ns = event.local_receive_ns
                        self._reason = None
                        self._events_accepted += 1
                        view = self._view_locked(event.local_receive_ns)
            elif event.event_type == "snapshot":
                rebuilt = self._builder.apply(event)
                if rebuilt is None:
                    self._reset_locked("invalid_snapshot")
                    self._sequence_errors += 1
                else:
                    self._last_update_ns = event.local_receive_ns
                    self._reason = None
                    self._events_accepted += 1
                view = self._view_locked(event.local_receive_ns)
            else:
                self._reset_locked("invalid_event_type")
                self._sequence_errors += 1
                view = self._view_locked(event.local_receive_ns)
        self._emit(view)

    def invalidate(self, reason: str = "invalid_message") -> None:
        with self._lock:
            self._reset_locked(reason)
            view = self._view_locked(time.monotonic_ns())
        self._emit(view)

    def connection_lost(self) -> None:
        self.invalidate("connection_lost")

    def snapshot(self, now_ns: int) -> OKXBookView:
        with self._lock:
            return self._view_locked(now_ns)

    def health(self, now_ns: int | None = None) -> dict[str, int | str | bool | float | None]:
        with self._lock:
            view = self._view_locked(now_ns if now_ns is not None else time.monotonic_ns())
            return {
                "venue": "okx",
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

    def _reset_locked(self, reason: str) -> None:
        self._builder = OrderBookBuilder("okx", self.symbol)
        self._last_update_ns = None
        self._reason = reason

    def _view_locked(self, now_ns: int) -> OKXBookView:
        book = self._builder.snapshot()
        clock_regressed = self._last_update_ns is not None and now_ns < self._last_update_ns
        age_ms = (
            None if self._last_update_ns is None or clock_regressed
            else (now_ns - self._last_update_ns) / 1_000_000
        )
        fresh = age_ms is not None and age_ms <= self.max_age_ms
        has_sides = bool(book.bids) and bool(book.asks)
        crossed = has_sides and book.best_bid is not None and book.best_ask is not None and book.best_bid >= book.best_ask
        eligible = self._builder.initialized and fresh and has_sides and not crossed and not clock_regressed
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
        return OKXBookView(
            venue="okx",
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

    def _emit(self, view: OKXBookView) -> None:
        try:
            self.on_book(view)
        except Exception:
            with self._lock:
                self._callback_errors += 1
