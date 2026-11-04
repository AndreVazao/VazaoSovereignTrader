from __future__ import annotations

import threading
import time
from typing import Any


class RuntimeObserverSnapshot:
    """Bounded latest-value mailbox for optional observer clients.

    Only a single small primitive payload is retained. Publishers replace the
    latest value; readers receive a copy. There is no queue, subscriber wait,
    callback, disk I/O, or network I/O in this class.
    """

    _FIELDS = (
        "ok",
        "status",
        "mode",
        "open_positions_count",
        "opportunities_count",
        "updated_at_ms",
        "health_state",
        "allow_new_tasks",
        "allow_risk_bearing_actions",
        "health_checked_at_ms",
    )
    _TEXT_LIMIT = 48
    _COUNT_MAX = 2_147_483_647
    _TIMESTAMP_MAX = 9_223_372_036_854_775_807

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._payload: dict[str, Any] = {
            "ok": True,
            "status": "OFF",
            "mode": "PAPER",
            "open_positions_count": 0,
            "opportunities_count": 0,
            "updated_at_ms": time.time_ns() // 1_000_000,
            "health_state": "unknown",
            "allow_new_tasks": False,
            "allow_risk_bearing_actions": False,
            "health_checked_at_ms": 0,
        }

    @classmethod
    def _bounded_text(cls, value: Any) -> str:
        return str(value)[: cls._TEXT_LIMIT]

    @staticmethod
    def _nonnegative_int(value: Any, default: int = 0, maximum: int = _TIMESTAMP_MAX) -> int:
        try:
            return min(maximum, max(0, int(value)))
        except (TypeError, ValueError, OverflowError):
            return default

    def publish(
        self,
        *,
        status: str,
        mode: str,
        open_positions_count: int,
        opportunities_count: int,
        updated_at_ms: int | None = None,
        health_state: str = "unknown",
        allow_new_tasks: bool = False,
        allow_risk_bearing_actions: bool = False,
        health_checked_at_ms: int = 0,
    ) -> None:
        """Replace the last value; slow readers never back-pressure publishers."""
        now_ms = time.time_ns() // 1_000_000
        payload = {
            "ok": True,
            "status": self._bounded_text(status),
            "mode": self._bounded_text(mode),
            "open_positions_count": self._nonnegative_int(
                open_positions_count, maximum=self._COUNT_MAX
            ),
            "opportunities_count": self._nonnegative_int(
                opportunities_count, maximum=self._COUNT_MAX
            ),
            "updated_at_ms": self._nonnegative_int(
                updated_at_ms, default=now_ms, maximum=self._TIMESTAMP_MAX
            ) or now_ms,
            "health_state": self._bounded_text(health_state),
            "allow_new_tasks": allow_new_tasks is True,
            "allow_risk_bearing_actions": False,
            "health_checked_at_ms": self._nonnegative_int(
                health_checked_at_ms, maximum=self._TIMESTAMP_MAX
            ),
        }
        with self._lock:
            self._payload = payload

    def read(self) -> dict[str, Any]:
        """Return a detached copy of the latest primitive-only payload."""
        with self._lock:
            return {field: self._payload[field] for field in self._FIELDS}
