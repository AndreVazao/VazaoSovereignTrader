from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class RealModeState:
    armed: bool = False
    armed_until: float = 0.0
    last_reason: str = "not armed"


class RealModeGuard:
    """Two-step guard for switching from PAPER to REAL.

    REAL mode should never be enabled by accident from the APK/dashboard.
    The user must provide the configured phrase, and the arming window expires.
    """

    def __init__(self, settings: dict):
        self.settings = settings
        self.state = RealModeState()

    @property
    def phrase(self) -> str:
        return str(self.settings.get("confirmation_phrase", "I_ACCEPT_REAL_RISK"))

    @property
    def arm_seconds(self) -> int:
        return int(self.settings.get("arm_seconds", 120))

    def arm(self, phrase: str) -> tuple[bool, str]:
        if phrase != self.phrase:
            self.state.armed = False
            self.state.armed_until = 0.0
            self.state.last_reason = "confirmation phrase mismatch"
            return False, self.state.last_reason
        self.state.armed = True
        self.state.armed_until = time.time() + self.arm_seconds
        self.state.last_reason = "armed"
        return True, "REAL mode armed temporarily"

    def disarm(self) -> None:
        self.state.armed = False
        self.state.armed_until = 0.0
        self.state.last_reason = "disarmed"

    def can_enable_real(self) -> tuple[bool, str]:
        if not self.state.armed:
            return False, self.state.last_reason or "REAL not armed"
        if time.time() > self.state.armed_until:
            self.disarm()
            self.state.last_reason = "REAL arming window expired"
            return False, self.state.last_reason
        return True, "REAL enabled with explicit confirmation"

    def snapshot(self) -> dict:
        remaining = max(0, int(self.state.armed_until - time.time())) if self.state.armed else 0
        return {
            "armed": self.state.armed and remaining > 0,
            "remaining_seconds": remaining,
            "last_reason": self.state.last_reason,
        }
