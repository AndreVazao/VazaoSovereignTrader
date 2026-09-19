from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class GateCheck:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class ReadinessReport:
    ready: bool
    status: str
    checks: tuple[GateCheck, ...]
    blockers: tuple[str, ...]

    def to_dict(self) -> dict:
        data = asdict(self)
        data["checks"] = [asdict(check) for check in self.checks]
        return data


class RealReadinessGate:
    """Evaluate protected REAL prerequisites without authorizing orders."""

    def evaluate(
        self, *, mode: str, preflight_ok: bool, state_samples: int,
        outcome_samples: int, eligible_outcomes: int,
        walk_forward_ok: bool, regime_validation_ok: bool,
        watchdog_ok: bool, recovery_ok: bool, execution_test_ok: bool,
        critical_errors: int = 0, credentials_ok: bool = True,
        credentials_detail: str = "not required", l2_oos_ok: bool = True,
        l2_oos_detail: str = "not required", reconciliation_ok: bool = True,
        reconciliation_detail: str = "not required",
        min_state_samples: int = 1000, min_outcome_samples: int = 1000,
        min_eligible_outcomes: int = 1,
    ) -> ReadinessReport:
        checks = (
            GateCheck("MODE_SUPPORTED", mode.upper() in {"PAPER", "REAL"}, f"mode={mode}"),
            GateCheck("PREFLIGHT", bool(preflight_ok), "exchange/config preflight"),
            GateCheck("MARKET_STATE_DATA", state_samples >= min_state_samples, f"samples={state_samples}/{min_state_samples}"),
            GateCheck("STATE_OUTCOMES", outcome_samples >= min_outcome_samples, f"outcomes={outcome_samples}/{min_outcome_samples}"),
            GateCheck("ELIGIBLE_OUTCOMES", eligible_outcomes >= min_eligible_outcomes, f"eligible={eligible_outcomes}/{min_eligible_outcomes}"),
            GateCheck("WALK_FORWARD", bool(walk_forward_ok), "chronological validation"),
            GateCheck("REGIME_VALIDATION", bool(regime_validation_ok), "regime validation"),
            GateCheck("L2_OOS", bool(l2_oos_ok), l2_oos_detail),
            GateCheck("PAPER_RECONCILIATION", bool(reconciliation_ok), reconciliation_detail),
            GateCheck("WATCHDOG", bool(watchdog_ok), "watchdog healthy"),
            GateCheck("RECOVERY", bool(recovery_ok), "recovery healthy"),
            GateCheck("EXECUTION_TEST", bool(execution_test_ok), "paper execution/rejection/recovery tests"),
            GateCheck("LIVE_CREDENTIALS", bool(credentials_ok), credentials_detail),
            GateCheck("CRITICAL_ERRORS", int(critical_errors) == 0, f"critical_errors={critical_errors}"),
        )
        blockers = tuple(check.name for check in checks if not check.passed)
        return ReadinessReport(
            ready=not blockers,
            status="READY_FOR_PROTECTED_REAL_REVIEW" if not blockers else "LOCKED",
            checks=checks,
            blockers=blockers,
        )
