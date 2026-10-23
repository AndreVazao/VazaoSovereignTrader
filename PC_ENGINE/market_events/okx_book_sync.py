from __future__ import annotations

import math
import threading
from dataclasses import dataclass
from typing import Callable

from .orderbook import OrderBookEvent, OrderBookLevel
from .orderbook_builder import OrderBookBuilder


@dataclass(frozen=True)
class OkxBookView:
    venue: str
    symbol: str
    status: str
    sequence: int | None
    bids: tuple[OrderBookLevel, ...]
    asks: tuple[OrderBookLevel, ...]
    age_ms: float | None
    eligible: bool
    reason: str | None
    observation_time_ns: int | None


class OkxBookSynchronizer:
    """Fail-closed synchronizer for OKX incremental books channel.

    The collector must reconnect after needs_resync becomes true. OKX snapshot
    channels are intentionally not used here because unchanged books may not
    be pushed frequently enough for short-horizon temporal comparisons.
    """

    def __init__(
        self,
        symbol: str,
        on_book: Callable[[OkxBookView], None],
        *,
        max_age_ms: float = 250.0,
    ) -> None:
        if not symbol or not symbol.strip():
            raise ValueError("invalid_symbol")
        try:
            age = float(max_age_ms)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("invalid_max_age") from exc
        if not math.isfinite(age) or age <= 0:
            raise ValueError("invalid_max_age")
        self.symbol = symbol
        self.max_age_ms = age
        self.on_book = on_book
        self._lock = threading.RLock()
        self._builder = OrderBookBuilder("okx", symbol)
        self._last_observation_ns: int | None = None
        self._reason: str | None = "awaiting_snapshot"
        self._needs_resync = True

    @property
    def needs_resync(self) -> bool:
        with self._lock:
            return self._needs_resync

    def on_event(self, event: OrderBookEvent) -> OkxBookView:
        now_ns = event.local_receive_ns
        with self._lock:
            if event.venue != "okx" or event.symbol != self.symbol:
                self._invalidate_locked("unexpected_event")
            elif (
                event.event_type == "delta"
                and self._builder.initialized
                and event.sequence == self._builder.snapshot().sequence
                and event.sequence_start == event.sequence + 1
                and not event.bids
                and not event.asks
            ):
                # OKX emits an empty incremental heartbeat with seqId == prevSeqId.
                # It confirms the connection is alive without changing book state.
                self._last_observation_ns = now_ns
                self._reason = None
                self._needs_resync = False
            else:
                reconstructed = self._builder.apply(event)
                if reconstructed is None or not self._builder.initialized:
                    self._invalidate_locked("sequence_or_book_invalid")
                else:
                    self._last_observation_ns = now_ns
                    self._reason = None
                    self._needs_resync = False
            view = self._view_locked(now_ns)
        self._emit(view)
        return view

    def connection_lost(self) -> OkxBookView:
        with self._lock:
            self._invalidate_locked("connection_lost")
            view = self._view_locked(None)
        self._emit(view)
        return view

    def snapshot(self, now_ns: int) -> OkxBookView:
        with self._lock:
            view = self._view_locked(now_ns)
        return view

    def health(self) -> dict:
        with self._lock:
            view = self._view_locked(None)
            return {
                "venue": "okx",
                "symbol": self.symbol,
                "status": view.status,
                "eligible": view.eligible,
                "sequence": view.sequence,
                "age_ms": view.age_ms,
                "reason": view.reason,
                "needs_resync": self._needs_resync,
            }

    def _invalidate_locked(self, reason: str) -> None:
        self._builder = OrderBookBuilder("okx", self.symbol)
        self._last_observation_ns = None
        self._reason = reason
        self._needs_resync = True

    def _view_locked(self, now_ns: int | None) -> OkxBookView:
        book = self._builder.snapshot()
        age_ms: float | None = None
        if now_ns is not None and self._last_observation_ns is not None:
            if now_ns < self._last_observation_ns:
                age_ms = None
            else:
                age_ms = (now_ns - self._last_observation_ns) / 1_000_000.0
        status = "SYNCED" if self._builder.initialized else "INVALID"
        reason = self._reason
        eligible = status == "SYNCED"
        if now_ns is None or self._last_observation_ns is None or age_ms is None:
            eligible = False
            reason = reason or "missing_observation_time"
        elif age_ms > self.max_age_ms:
            eligible = False
            reason = "stale_book"
        if not book.bids or not book.asks:
            eligible = False
            reason = "one_sided_book"
        elif book.best_bid is None or book.best_ask is None or book.best_bid >= book.best_ask:
            eligible = False
            reason = "crossed_or_invalid_book"
        return OkxBookView(
            venue="okx",
            symbol=self.symbol,
            status=status,
            sequence=book.sequence,
            bids=book.bids,
            asks=book.asks,
            age_ms=age_ms,
            eligible=eligible,
            reason=reason,
            observation_time_ns=self._last_observation_ns,
        )

    def _emit(self, view: OkxBookView) -> None:
        self.on_book(view)
