from PC_ENGINE.core.real_readiness import RealReadinessGate


def test_gate_locks_with_missing_evidence():
    report = RealReadinessGate().evaluate(
        mode="PAPER",
        preflight_ok=True,
        state_samples=999,
        outcome_samples=0,
        eligible_outcomes=0,
        walk_forward_ok=True,
        regime_validation_ok=True,
        watchdog_ok=True,
        recovery_ok=True,
        execution_test_ok=True,
    )
    assert report.ready is False
    assert report.status == "LOCKED"
    assert "MARKET_STATE_DATA" in report.blockers
    assert "STATE_OUTCOMES" in report.blockers


def test_gate_requires_all_checks_before_review_ready():
    report = RealReadinessGate().evaluate(
        mode="PAPER",
        preflight_ok=True,
        state_samples=1000,
        outcome_samples=1000,
        eligible_outcomes=1,
        walk_forward_ok=True,
        regime_validation_ok=True,
        watchdog_ok=True,
        recovery_ok=True,
        execution_test_ok=True,
    )
    assert report.ready is True
    assert report.status == "READY_FOR_PROTECTED_REAL_REVIEW"
    assert report.blockers == ()


def test_real_mode_never_passes_the_gate():
    report = RealReadinessGate().evaluate(
        mode="REAL",
        preflight_ok=True,
        state_samples=1000,
        outcome_samples=1000,
        eligible_outcomes=1,
        walk_forward_ok=True,
        regime_validation_ok=True,
        watchdog_ok=True,
        recovery_ok=True,
        execution_test_ok=True,
    )
    assert report.ready is False
    assert "MODE_PAPER" in report.blockers
