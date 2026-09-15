from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class RealModeState:
    armed: bool = False
    armed_until: float = 0.0
    last_reason: str = "not armed"


class RealModeGuard:
    """Explicit operator authorization required before protected REAL mode."""

    def __init__(self, settings: dict):
        self.settings = settings
        self.state = RealModeState()

    @property
    def enabled(self) -> bool:
        return bool(self.settings.get("enabled", True))

    @property
    def phrase(self) -> str:
        return str(self.settings.get("confirmation_phrase", "EU ACEITO O RISCO"))

    @property
    def arm_seconds(self) -> int:
        return max(30, int(self.settings.get("arm_seconds", 300)))

    def arm(self, phrase: str) -> tuple[bool, str]:
        if not self.enabled:
            self.state.last_reason = "REAL mode guard disabled by configuration"
            return False, self.state.last_reason
        if phrase != self.phrase:
            self.disarm("confirmation phrase mismatch")
            return False, self.state.last_reason
        self.state.armed = True
        self.state.armed_until = time.time() + self.arm_seconds
        self.state.last_reason = "armed"
        return True, "REAL mode armed temporarily"

    def disarm(self, reason: str = "disarmed") -> None:
        self.state.armed = False
        self.state.armed_until = 0.0
        self.state.last_reason = reason

    def can_enable_real(self) -> tuple[bool, str]:
        if not self.enabled:
            return False, "REAL mode guard disabled by configuration"
        if not self.state.armed:
            return False, self.state.last_reason or "REAL not armed"
        if time.time() >= self.state.armed_until:
            self.disarm("REAL arming window expired")
            return False, self.state.last_reason
        return True, "REAL enabled with explicit confirmation"

    def consume(self) -> tuple[bool, str]:
        ok, reason = self.can_enable_real()
        if not ok:
            return False, reason
        self.disarm("authorization consumed")
        return True, "REAL authorization consumed"

    def snapshot(self) -> dict:
        remaining = max(0, int(self.state.armed_until - time.time())) if self.state.armed else 0
        return {"armed": self.state.armed and remaining > 0, "remaining_seconds": remaining, "last_reason": self.state.last_reason}
