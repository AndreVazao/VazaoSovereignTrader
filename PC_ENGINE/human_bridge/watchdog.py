from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any

from .bridge import HumanInteractionBridge


@dataclass
class HumanBridgeHeartbeat:
    mobile_last_seen: float = 0.0
    pc_last_seen: float = 0.0


class HumanBridgeWatchdog:
    """Control-plane watchdog for human browser bridge.

    It never submits trades and never solves CAPTCHA/2FA. It only reports
    liveness and expires/cancels stale human-interaction work.
    """

    def __init__(self, bridge: HumanInteractionBridge, config: dict[str, Any] | None = None):
        cfg = config or {}
        self.bridge = bridge
        self.mobile_timeout_seconds = max(10.0, float(cfg.get("mobile_timeout_seconds", 30)))
        self.pc_timeout_seconds = max(10.0, float(cfg.get("pc_timeout_seconds", 30)))
        self.responded_timeout_seconds = max(30.0, float(cfg.get("responded_timeout_seconds", 120)))
        self._state = HumanBridgeHeartbeat()
        self._lock = threading.RLock()

    def heartbeat(self, source: str) -> dict[str, Any]:
        now = time.time()
        with self._lock:
            if source == "mobile":
                self._state.mobile_last_seen = now
            elif source == "pc":
                self._state.pc_last_seen = now
            else:
                raise ValueError("source must be mobile or pc")
        return self.snapshot()

    def check(self, now: float | None = None) -> dict[str, Any]:
        now = time.time() if now is None else float(now)
        expired = self.bridge.expire_stale()
        stale_responded = 0
        for item in self.bridge.snapshot()["requests"]:
            if item.get("status") == "RESPONDED" and now - float(item.get("updated_at", now)) >= self.responded_timeout_seconds:
                if self.bridge.cancel(item["request_id"]):
                    stale_responded += 1
        with self._lock:
            mobile_age = self._age(self._state.mobile_last_seen, now)
            pc_age = self._age(self._state.pc_last_seen, now)
        return {
            "ok": mobile_age <= self.mobile_timeout_seconds and pc_age <= self.pc_timeout_seconds,
            "safe_state": mobile_age > self.mobile_timeout_seconds or pc_age > self.pc_timeout_seconds,
            "mobile": {"last_seen": self._state.mobile_last_seen, "age_seconds": mobile_age, "stale": mobile_age > self.mobile_timeout_seconds},
            "pc": {"last_seen": self._state.pc_last_seen, "age_seconds": pc_age, "stale": pc_age > self.pc_timeout_seconds},
            "expired_requests": expired,
            "cancelled_stuck_responses": stale_responded,
        }

    def snapshot(self) -> dict[str, Any]:
        return self.check()

    @staticmethod
    def _age(last_seen: float, now: float) -> float:
        return float("inf") if last_seen <= 0 else max(0.0, now - last_seen)
