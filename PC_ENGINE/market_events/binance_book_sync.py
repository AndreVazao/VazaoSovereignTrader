from __future__ import annotations

import json
import threading
import time
from collections import deque
from typing import Callable
from urllib.parse import urlencode
from urllib.request import urlopen

from .binance_book_state import BinanceSpotDepthBook, BookSnapshot, BookStatus
from .orderbook import OrderBookEvent, OrderBookLevel


SnapshotPayload = tuple[int, tuple[OrderBookLevel, ...], tuple[OrderBookLevel, ...]]
SnapshotFetcher = Callable[[str], SnapshotPayload]
BookCallback = Callable[[BookSnapshot], None]


def fetch_binance_spot_snapshot(symbol: str, timeout_seconds: float = 5.0) -> SnapshotPayload:
    """Fetch one public Binance Spot REST snapshot; never submits an order."""
    market = symbol.replace("/", "").upper()
    if not market or not market.isalnum():
        raise ValueError("invalid_symbol")
    query = urlencode({"symbol": market, "limit": 1000})
    url = "https://api.binance.com/api/v3/depth?" + query
    with urlopen(url, timeout=timeout_seconds) as response:
        payload = json.load(response)
    update_id = payload.get("lastUpdateId")
    if not isinstance(update_id, int) or isinstance(update_id, bool) or update_id < 0:
        raise ValueError("invalid_snapshot_id")

    def levels(rows: object) -> tuple[OrderBookLevel, ...]:
        if not isinstance(rows, list):
            raise ValueError("invalid_snapshot_levels")
        result: list[OrderBookLevel] = []
        for row in rows:
            if not isinstance(row, (list, tuple)) or len(row) < 2:
                raise ValueError("invalid_snapshot_level")
            try:
                result.append(OrderBookLevel(float(row[0]), float(row[1])))
            except (TypeError, ValueError, OverflowError) as exc:
                raise ValueError("invalid_snapshot_level") from exc
        return tuple(result)

    return update_id, levels(payload.get("bids")), levels(payload.get("asks"))


class BinanceSpotBookSynchronizer:
    """Bounded WS-buffer + REST-snapshot replay + sequence-gap recovery.

    The output callback receives synchronized views and explicit invalidation
    snapshots (eligible=False) when a gap, overflow, disconnect, or snapshot
    failure is detected. Consumers must still enforce the view's freshness
    limit at read time because no new WebSocket event may arrive to announce
    staleness. Raw events are diagnostic only; no signals or orders are produced.
    """

    def __init__(
        self,
        symbol: str,
        on_book: BookCallback,
        snapshot_fetcher: SnapshotFetcher = fetch_binance_spot_snapshot,
        *,
        max_buffer_events: int = 2000,
        max_age_ms: float = 1000.0,
        max_levels: int = 1000,
    ) -> None:
        if max_buffer_events < 1:
            raise ValueError("max_buffer_events must be positive")
        self.symbol = symbol
        self.on_book = on_book
        self.snapshot_fetcher = snapshot_fetcher
        self.max_buffer_events = max_buffer_events
        self.book = BinanceSpotDepthBook(symbol, max_age_ms=max_age_ms, max_levels=max_levels)
        self._buffer: deque[OrderBookEvent] = deque()
        self._condition = threading.Condition()
        self._need_snapshot = False
        self._buffer_overflow = False
        self._closed = False
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._snapshot_attempts = 0
        self._snapshot_errors = 0
        self._sequence_gaps = 0
        self._buffer_overflows = 0
        self._callback_errors = 0

    def start(self) -> None:
        with self._condition:
            if self._closed:
                raise RuntimeError("synchronizer_closed")
            if self._thread is not None:
                return
            self._need_snapshot = True
            self._thread = threading.Thread(
                target=self._snapshot_worker,
                name=f"binance-book-sync-{self.symbol.replace('/', '')}",
                daemon=True,
            )
            self._thread.start()

    def on_event(self, event: OrderBookEvent) -> None:
        view: BookSnapshot | None = None
        with self._condition:
            if self._closed or event.venue != "binance" or event.symbol != self.symbol:
                return
            if self.book.update_id is not None and self.book.status != BookStatus.INVALID:
                accepted = self.book.apply_delta(event)
                if self.book.status == BookStatus.INVALID:
                    if self.book.reason == "sequence_gap":
                        self._sequence_gaps += 1
                    self._buffer.clear()
                    self._schedule_snapshot_locked()
                    view = self.book.snapshot(event.local_receive_ns)
                elif accepted:
                    view = self.book.snapshot(event.local_receive_ns)
            else:
                if len(self._buffer) >= self.max_buffer_events:
                    self._buffer.clear()
                    self._buffer_overflow = True
                    self._buffer_overflows += 1
                    self.book.invalidate("buffer_overflow")
                    self._schedule_snapshot_locked()
                    view = self.book.snapshot(event.local_receive_ns)
                else:
                    self._buffer.append(event)
                    self._condition.notify_all()
        # Persist both eligible books and explicit ineligible states so a
        # consumer can clear its last known good view after a discontinuity.
        if view is not None:
            self._emit(view)

    def install_snapshot(self, snapshot: SnapshotPayload) -> bool:
        """Install and replay buffered events; exposed for deterministic tests."""
        update_id, bids, asks = snapshot
        view: BookSnapshot | None = None
        applied = False
        with self._condition:
            if self._closed:
                return False
            if self._buffer_overflow:
                self._buffer_overflow = False
                self._buffer.clear()
                self.book.invalidate("buffer_overflow")
                self._schedule_snapshot_locked()
                view = self.book.snapshot(time.monotonic_ns())
            elif not self.book.install_snapshot(update_id, bids, asks):
                self._buffer.clear()
                self._schedule_snapshot_locked()
                view = self.book.snapshot(time.monotonic_ns())
            else:
                buffered = list(self._buffer)
                self._buffer.clear()
                for event in buffered:
                    self.book.apply_delta(event)
                    if self.book.status == BookStatus.INVALID:
                        if self.book.reason == "sequence_gap":
                            self._sequence_gaps += 1
                        self._buffer.clear()
                        self._schedule_snapshot_locked()
                        view = self.book.snapshot(event.local_receive_ns)
                        break
                else:
                    applied = self.book.status != BookStatus.INVALID
                    if self.book.status == BookStatus.SYNCED:
                        view = self.book.snapshot(time.monotonic_ns())
        if view is not None:
            self._emit(view)
        return applied

    def invalidate(self, reason: str = "invalid_message") -> None:
        """Fail closed after an untrustworthy depth message and request a fresh snapshot."""
        with self._condition:
            if self._closed:
                return
            self._buffer.clear()
            self.book.invalidate(reason)
            self._schedule_snapshot_locked()
            view = self.book.snapshot(time.monotonic_ns())
        self._emit(view)

    def connection_lost(self) -> None:
        """Fail closed after a WebSocket disconnect and request a fresh snapshot."""
        self.invalidate("connection_lost")

    def health(self) -> dict[str, int | str | None | bool]:
        with self._condition:
            current_view = self.book.snapshot(time.monotonic_ns())
            return {
                "symbol": self.symbol,
                "state": self.book.status.value,
                "update_id": self.book.update_id,
                "eligible": current_view.eligible,
                "age_ms": current_view.age_ms,
                "view_reason": current_view.reason,
                "buffered_events": len(self._buffer),
                "snapshot_attempts": self._snapshot_attempts,
                "snapshot_errors": self._snapshot_errors,
                "sequence_gaps": self._sequence_gaps,
                "buffer_overflows": self._buffer_overflows,
                "callback_errors": self._callback_errors,
                "last_reason": self.book.reason,
                "running": self._thread is not None and self._thread.is_alive() and not self._closed,
            }

    def stop(self) -> None:
        with self._condition:
            self._closed = True
            self._stop_event.set()
            self._condition.notify_all()
            thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=2.0)

    def _schedule_snapshot_locked(self) -> None:
        self._need_snapshot = True
        self._condition.notify_all()

    def _snapshot_worker(self) -> None:
        retry_seconds = 0.5
        while True:
            with self._condition:
                while not self._closed and not self._need_snapshot:
                    self._condition.wait()
                if self._closed:
                    return
                self._need_snapshot = False
                self._snapshot_attempts += 1
            try:
                snapshot = self.snapshot_fetcher(self.symbol)
            except Exception as exc:
                with self._condition:
                    self._snapshot_errors += 1
                    self.book.invalidate("snapshot_fetch_" + type(exc).__name__)
                    self._need_snapshot = True
                    view = self.book.snapshot(time.monotonic_ns())
                self._emit(view)
                if self._stop_event.wait(retry_seconds):
                    return
                retry_seconds = min(30.0, retry_seconds * 2.0)
                continue
            applied = self.install_snapshot(snapshot)
            if applied:
                retry_seconds = 0.5
            else:
                with self._condition:
                    if self._closed:
                        return
                    should_retry = self._need_snapshot
                if should_retry and self._stop_event.wait(retry_seconds):
                    return
                retry_seconds = min(30.0, retry_seconds * 2.0)

    def _emit(self, view: BookSnapshot) -> None:
        try:
            self.on_book(view)
        except Exception:
            with self._condition:
                self._callback_errors += 1
