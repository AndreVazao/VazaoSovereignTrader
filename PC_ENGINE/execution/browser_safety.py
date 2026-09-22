from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from typing import Iterable


class BrowserSafetyStatus(str, Enum):
    READY = "READY"
    STALE = "STALE"
    TARGET_INVALID = "TARGET_INVALID"
    COVERED = "COVERED"
    CONTEXT_CHANGED = "CONTEXT_CHANGED"
    OUTCOME_UNVERIFIED = "OUTCOME_UNVERIFIED"
    HUMAN_REQUIRED = "HUMAN_REQUIRED"


@dataclass(frozen=True)
class BrowserElement:
    target_id: str
    role: str
    name: str = ""
    visible: bool = True
    enabled: bool = True
    covered: bool = False


@dataclass(frozen=True)
class BrowserObservation:
    page_fingerprint: str
    context_fingerprint: str
    observed_ts_ms: int
    elements: tuple[BrowserElement, ...]

    @classmethod
    def from_elements(cls, *, page_fingerprint: str, context_fingerprint: str, observed_ts_ms: int, elements: Iterable[BrowserElement]) -> "BrowserObservation":
        return cls(page_fingerprint, context_fingerprint, int(observed_ts_ms), tuple(elements))

    def target(self, target_id: str) -> BrowserElement | None:
        return next((e for e in self.elements if e.target_id == target_id), None)


@dataclass(frozen=True)
class BrowserActionProposal:
    operation: str
    target_id: str
    confidence: float
    page_fingerprint: str
    context_fingerprint: str


@dataclass(frozen=True)
class BrowserVerification:
    status: BrowserSafetyStatus
    external_id: str | None = None
    detail: str | None = None


class BrowserFreshnessGuard:
    """Fail-closed observed-target guard inspired by Jev's indexed DOM model.

    The model proposes an operation and observed target id only. It cannot supply
    selectors, coordinates, shell commands or executable JavaScript.
    """

    def validate(self, observation: BrowserObservation, proposal: BrowserActionProposal) -> BrowserSafetyStatus:
        if observation.page_fingerprint != proposal.page_fingerprint:
            return BrowserSafetyStatus.STALE
        if observation.context_fingerprint != proposal.context_fingerprint:
            return BrowserSafetyStatus.CONTEXT_CHANGED
        target = observation.target(proposal.target_id)
        if target is None or not target.visible or not target.enabled:
            return BrowserSafetyStatus.TARGET_INVALID
        if target.covered:
            return BrowserSafetyStatus.COVERED
        if not 0.0 <= proposal.confidence <= 1.0:
            return BrowserSafetyStatus.TARGET_INVALID
        return BrowserSafetyStatus.READY


class BrowserExecutionSafety:
    """Safety boundary around browser submission and independent verification."""

    FORBIDDEN_OPERATIONS = frozenset({"JAVASCRIPT", "SHELL", "SELECTOR", "COORDINATE", "CAPTCHA"})

    def __init__(self, *, freshness_guard: BrowserFreshnessGuard | None = None):
        self.freshness_guard = freshness_guard or BrowserFreshnessGuard()

    def authorize(self, observation: BrowserObservation, proposal: BrowserActionProposal) -> BrowserSafetyStatus:
        if proposal.operation.upper() in self.FORBIDDEN_OPERATIONS:
            return BrowserSafetyStatus.HUMAN_REQUIRED if proposal.operation.upper() == "CAPTCHA" else BrowserSafetyStatus.TARGET_INVALID
        return self.freshness_guard.validate(observation, proposal)

    @staticmethod
    def verify_exchange_outcome(*, exchange_status: str | None, external_id: str | None = None) -> BrowserVerification:
        status = str(exchange_status or "").upper().strip()
        if status in {"FILLED", "PARTIALLY_FILLED", "CANCELLED", "REJECTED"}:
            return BrowserVerification(BrowserSafetyStatus.READY, external_id=external_id, detail=status)
        return BrowserVerification(BrowserSafetyStatus.OUTCOME_UNVERIFIED, external_id=external_id, detail=status or "missing exchange status")


def fingerprint_context(values: Iterable[str]) -> str:
    canonical = "|".join(str(v) for v in values)
    return sha256(canonical.encode("utf-8")).hexdigest()
