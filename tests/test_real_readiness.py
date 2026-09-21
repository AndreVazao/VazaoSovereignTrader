from PC_ENGINE.core.real_readiness import RealReadinessGate


def test_gate_blocks_without_evidence():
    report = RealReadinessGate().evaluate(
        mode="PAPER", preflight_ok=True, state_samples=999,
        outcome_samples=0, eligible_outcomes=0,
        walk_forward_ok=True, regime_validation_ok=True,
        watchdog_ok=True, recovery_ok=True, execution_test_ok=True,
    )
    assert not report.ready
    assert report.status == "LOCKED"
    assert "MARKET_STATE_DATA" in report.blockers
    assert "STATE_OUTCOMES" in report.blockers


def test_gate_requires_all_checks():
    report = RealReadinessGate().evaluate(
        mode="PAPER", preflight_ok=True, state_samples=1000,
        outcome_samples=1000, eligible_outcomes=1,
        walk_forward_ok=True, regime_validation_ok=True,
        watchdog_ok=True, recovery_ok=True, execution_test_ok=True,
    )
    assert report.ready
    assert report.status == "READY_FOR_PROTECTED_REAL_REVIEW"


def test_real_mode_is_supported_but_does_not_authorize_execution():
    report = RealReadinessGate().evaluate(
        mode="REAL", preflight_ok=True, state_samples=1000,
        outcome_samples=1000, eligible_outcomes=1,
        walk_forward_ok=True, regime_validation_ok=True,
        watchdog_ok=True, recovery_ok=True, execution_test_ok=True,
    )
    assert report.ready
    assert report.status == "READY_FOR_PROTECTED_REAL_REVIEW"


def test_gate_blocks_financial_reconciliation_mismatch_even_if_legacy_flag_is_true():
    report = RealReadinessGate().evaluate(
        mode="REAL", preflight_ok=True, state_samples=1000,
        outcome_samples=1000, eligible_outcomes=1,
        walk_forward_ok=True, regime_validation_ok=True,
        watchdog_ok=True, recovery_ok=True, execution_test_ok=True,
        reconciliation_ok=True,
        account_reconciliation={"ok": False, "quote_mismatch": True},
    )
    assert not report.ready
    assert "PAPER_RECONCILIATION" in report.blockers
