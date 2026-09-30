# Path: PC_ENGINE/core/execution_gate.py
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ExecutionState(str, Enum):
    PAPER = "PAPER"
    REAL_AUTH_REQUIRED = "REAL_AUTH_REQUIRED"
    REAL_AUTHORIZED = "REAL_AUTHORIZED"
    REAL_ACTIVE = "REAL_ACTIVE"
    SAFEGUARD_PAPER = "SAFEGUARD_PAPER"
    REAL_RECOVERY_ELIGIBLE = "REAL_RECOVERY_ELIGIBLE"


@dataclass(frozen=True)
class GateDecision:
    allowed: bool
    state: ExecutionState
    reason: str


class ExecutionGate:
    """Fail-closed state machine for protected execution.

    The first transition into protected REAL requires an explicit human
    authorization. Recovery can become eligible automatically after a
    fail-safe, but it can never manufacture the first authorization.
    """

    def __init__(self) -> None:
        self.state = ExecutionState.PAPER
        self._human_authorized = False

    @property
    def human_authorized(self) -> bool:
        return self._human_authorized

    def human_authorize(self) -> GateDecision:
        self._human_authorized = True
        self.state = ExecutionState.REAL_AUTHORIZED
        return GateDecision(True, self.state, "initial human REAL authorization accepted")

    def activate_real(self) -> GateDecision:
        if not self._human_authorized:
            self.state = ExecutionState.REAL_AUTH_REQUIRED
            return GateDecision(False, self.state, "initial human REAL authorization required")
        if self.state not in {
            ExecutionState.REAL_AUTHORIZED,
            ExecutionState.REAL_RECOVERY_ELIGIBLE,
        }:
            return GateDecision(False, self.state, "REAL activation not eligible from current state")
        self.state = ExecutionState.REAL_ACTIVE
        return GateDecision(True, self.state, "REAL execution activated")

    def fail_safe(self, reason: str) -> GateDecision:
        self.state = ExecutionState.SAFEGUARD_PAPER
        return GateDecision(True, self.state, reason)

    def evaluate_recovery(self, *, readiness_ok: bool, reconciliation_ok: bool, timing_ok: bool) -> GateDecision:
        if not self._human_authorized:
            self.state = ExecutionState.REAL_AUTH_REQUIRED
            return GateDecision(False, self.state, "initial human REAL authorization required")
        if not (readiness_ok and reconciliation_ok and timing_ok):
            self.state = ExecutionState.SAFEGUARD_PAPER
            return GateDecision(False, self.state, "REAL recovery gates not satisfied")
        self.state = ExecutionState.REAL_RECOVERY_ELIGIBLE
        return GateDecision(True, self.state, "REAL recovery eligible")

    def can_submit(self, *, opportunity_ok: bool, risk_ok: bool, exchange_ok: bool, stale_ok: bool) -> GateDecision:
        if self.state != ExecutionState.REAL_ACTIVE:
            return GateDecision(False, self.state, "execution state is not REAL_ACTIVE")
        if not all((opportunity_ok, risk_ok, exchange_ok, stale_ok)):
            return GateDecision(False, self.state, "execution opportunity/risk/exchange/stale gate failed")
        return GateDecision(True, self.state, "execution permitted")

    def reset_to_paper(self) -> GateDecision:
        self.state = ExecutionState.PAPER
        return GateDecision(True, self.state, "returned to PAPER")
