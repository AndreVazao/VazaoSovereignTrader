from __future__ import annotations

import math
import threading
import time
from typing import Any


class TopOfBookQualityGate:
    """Validate public ticker observations without inventing cross-venue timing."""

    MAX_LOCAL_RECEIVE_AGE_NS = 30_000_000_000
    FUTURE_MONOTONIC_TOLERANCE_NS = 100_000_000

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._last_provider: dict[tuple[str, str], tuple[int, float, float]] = {}
        self._counters: dict[str, int] = {
            "accepted": 0,
            "provider_timestamp_missing": 0,
            "same_timestamp_different_quote": 0,
            "rejected_invalid_quote": 0,
            "rejected_invalid_receive_clock": 0,
            "rejected_invalid_provider_timestamp": 0,
            "rejected_out_of_order_provider_timestamp": 0,
            "rejected_duplicate_provider_observation": 0,
        }

    @staticmethod
    def _finite_positive(value: Any) -> float | None:
        if isinstance(value, bool):
            return None
        try:
            number = float(value)
        except (TypeError, ValueError, OverflowError):
            return None
        return number if math.isfinite(number) and number > 0 else None

    def evaluate(
        self,
        event: Any,
        *,
        now_monotonic_ns: int | None = None,
    ) -> tuple[bool, str | None]:
        """Return (accepted, timestamp_quality/rejection_reason).

        Provider timestamps are ordered only within the same venue/instrument.
        They are never compared with the local wall clock because clock offset
        and timestamp semantics are not calibrated across venues.
        """
        bid = self._finite_positive(getattr(event, "bid", None))
        ask = self._finite_positive(getattr(event, "ask", None))
        if bid is None or ask is None or ask <= bid:
            return self._reject("rejected_invalid_quote")

        try:
            receive_ns = int(event.local_receive_ns)
            receive_wall_ns = int(event.local_receive_wall_ns)
            now_ns = int(now_monotonic_ns if now_monotonic_ns is not None else time.monotonic_ns())
        except (AttributeError, TypeError, ValueError, OverflowError):
            return self._reject("rejected_invalid_receive_clock")

        age_ns = now_ns - receive_ns
        if (
            receive_ns <= 0
            or receive_wall_ns <= 0
            or age_ns < -self.FUTURE_MONOTONIC_TOLERANCE_NS
            or age_ns > self.MAX_LOCAL_RECEIVE_AGE_NS
        ):
            return self._reject("rejected_invalid_receive_clock")

        raw_provider_ts = getattr(event, "provider_ts_ms", None)
        if raw_provider_ts is None:
            with self._lock:
                self._counters["accepted"] += 1
                self._counters["provider_timestamp_missing"] += 1
            return True, "LOCAL_RECEIVE_ONLY"

        if isinstance(raw_provider_ts, bool):
            return self._reject("rejected_invalid_provider_timestamp")
        try:
            provider_ts = int(raw_provider_ts)
        except (TypeError, ValueError, OverflowError):
            return self._reject("rejected_invalid_provider_timestamp")
        if provider_ts <= 0:
            return self._reject("rejected_invalid_provider_timestamp")

        venue = str(getattr(event, "venue", "")).strip().lower()
        symbol = str(getattr(event, "symbol", "")).strip().upper()
        if not venue or not symbol:
            return self._reject("rejected_invalid_provider_timestamp")

        key = (venue, symbol)
        with self._lock:
            previous = self._last_provider.get(key)
            if previous is not None:
                previous_ts, previous_bid, previous_ask = previous
                if provider_ts < previous_ts:
                    self._counters["rejected_out_of_order_provider_timestamp"] += 1
                    return False, "OUT_OF_ORDER_PROVIDER_TIMESTAMP"
                if provider_ts == previous_ts:
                    if bid == previous_bid and ask == previous_ask:
                        self._counters["rejected_duplicate_provider_observation"] += 1
                        return False, "DUPLICATE_PROVIDER_OBSERVATION"
                    self._counters["same_timestamp_different_quote"] += 1
                    self._last_provider[key] = (provider_ts, bid, ask)
                    self._counters["accepted"] += 1
                    return True, "SAME_TIMESTAMP_DIFFERENT_QUOTE"
            self._last_provider[key] = (provider_ts, bid, ask)
            self._counters["accepted"] += 1
        return True, "PROVIDER_TIMESTAMP_ORDERED"

    def _reject(self, reason: str) -> tuple[bool, str]:
        with self._lock:
            self._counters[reason] += 1
        return False, reason.upper()

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return dict(self._counters)
