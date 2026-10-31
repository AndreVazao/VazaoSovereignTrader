"""Fail-closed health policy for VST agents and departments.

This module computes a recommended health/isolation decision only. It does not
stop workers, change trading permissions, or mutate runtime state; callers must
apply the decision through the authoritative runtime control plane and audit it.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class HealthState(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    QUARANTINED = "quarantined"
    RECOVERING = "recovering"


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass(frozen=True)
class HealthSignal:
    code: str
    severity: Severity
    message: str = ""


@dataclass(frozen=True)
class HealthDecision:
    state: HealthState
    isolate: bool
    allow_new_tasks: bool
    allow_risk_bearing_actions: bool
    reasons: tuple[str, ...]


def evaluate_health(
    signals: Iterable[HealthSignal],
    *,
    manually_quarantined: bool = False,
    currently_quarantined: bool = False,
    recovery_checks_passed: bool = False,
) -> HealthDecision:
    """Return a conservative policy decision from trusted, structured signals.

    Quarantine is sticky: a quarantined component cannot self-release merely
    because the current signal list is empty. Release requires an explicit
    recovery transition and passing checks, applied by an authorized operator
    or control-plane policy.
    """
    items = tuple(signals)
    critical = tuple(s for s in items if s.severity is Severity.CRITICAL)
    errors = tuple(s for s in items if s.severity is Severity.ERROR)
    warnings = tuple(s for s in items if s.severity is Severity.WARNING)

    if manually_quarantined or critical:
        reasons = tuple(
            (["manual_quarantine"] if manually_quarantined else [])
            + [f"{s.code}:{s.severity.value}" for s in critical]
        )
        return HealthDecision(
            HealthState.QUARANTINED, True, False, False, reasons
        )

    if currently_quarantined:
        if recovery_checks_passed:
            return HealthDecision(
                HealthState.RECOVERING, True, False, False,
                ("recovery_checks_passed; operator/control-plane release required",),
            )
        return HealthDecision(
            HealthState.QUARANTINED, True, False, False,
            ("quarantine_sticky_until_recovery_checks_pass",),
        )

    if errors:
        return HealthDecision(
            HealthState.DEGRADED, False, False, False,
            tuple(f"{s.code}:{s.severity.value}" for s in errors),
        )

    if warnings:
        return HealthDecision(
            HealthState.DEGRADED, False, True, False,
            tuple(f"{s.code}:{s.severity.value}" for s in warnings),
        )

    return HealthDecision(HealthState.HEALTHY, False, True, True, ())
