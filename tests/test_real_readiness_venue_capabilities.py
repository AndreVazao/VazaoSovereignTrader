from PC_ENGINE.core.real_readiness import RealReadinessGate


def test_real_readiness_can_block_unverified_venue_capabilities():
    report = RealReadinessGate().evaluate(
        mode="REAL",
        preflight_ok=True,
        state_samples=1000,
        outcome_samples=1000,
        eligible_outcomes=1,
        eligible_outcome_samples=300,
        walk_forward_ok=True,
        regime_validation_ok=True,
        watchdog_ok=True,
        recovery_ok=True,
        execution_test_ok=True,
        capabilities_ok=False,
        capabilities_detail="TEST:real_order_submit:not_verified",
    )
    assert not report.ready
    assert "VENUE_CAPABILITIES" in report.blockers
