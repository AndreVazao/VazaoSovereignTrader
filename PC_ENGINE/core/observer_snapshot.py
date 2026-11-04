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
        payload = {
            "ok": True,
            "status": str(status),
            "mode": str(mode),
            "open_positions_count": max(0, int(open_positions_count)),
            "opportunities_count": max(0, int(opportunities_count)),
            "updated_at_ms": int(updated_at_ms or time.time_ns() // 1_000_000),
            "health_state": str(health_state),
            "allow_new_tasks": bool(allow_new_tasks),
            "allow_risk_bearing_actions": False,
            "health_checked_at_ms": max(0, int(health_checked_at_ms)),
        }
        with self._lock:
            self._payload = payload

    def read(self) -> dict[str, Any]:
        """Return a detached copy of the latest primitive-only payload."""
        with self._lock:
            return {field: self._payload[field] for field in self._FIELDS}
