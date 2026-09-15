from PC_ENGINE.core.real_readiness import RealReadinessGate


def test_readiness_gate_is_locked_by_default():
    report = RealReadinessGate().evaluate(
        mode="PAPER", preflight_ok=False, state_samples=0, outcome_samples=0,
        eligible_outcomes=0, walk_forward_ok=False, regime_validation_ok=False,
        watchdog_ok=False, recovery_ok=False, execution_test_ok=False,
    )
    assert report.status == "LOCKED"
    assert report.ready is False
    assert report.blockers
