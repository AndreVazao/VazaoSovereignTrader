from PC_ENGINE.tools.health_isolation import (
    HealthSignal, HealthState, Severity, evaluate_health,
)


def test_critical_signal_recommends_quarantine_and_blocks_risk_actions():
    decision = evaluate_health([
        HealthSignal("integrity_check_failed", Severity.CRITICAL),
    ])
    assert decision.state is HealthState.QUARANTINED
    assert decision.isolate is True
    assert decision.allow_new_tasks is False
    assert decision.allow_risk_bearing_actions is False


def test_manual_quarantine_is_sticky_even_without_signals():
    decision = evaluate_health([], manually_quarantined=True)
    assert decision.state is HealthState.QUARANTINED
    assert decision.isolate is True
    assert decision.allow_risk_bearing_actions is False


def test_existing_quarantine_cannot_self_release_on_empty_signals():
    decision = evaluate_health([], currently_quarantined=True)
    assert decision.state is HealthState.QUARANTINED
    assert decision.isolate is True


def test_recovery_checks_only_move_to_recovering_not_healthy():
    decision = evaluate_health([], currently_quarantined=True, recovery_checks_passed=True)
    assert decision.state is HealthState.RECOVERING
    assert decision.isolate is True
    assert decision.allow_new_tasks is False
    assert decision.allow_risk_bearing_actions is False


def test_error_degrades_and_blocks_new_tasks_without_auto_isolating():
    decision = evaluate_health([HealthSignal("repeated_timeout", Severity.ERROR)])
    assert decision.state is HealthState.DEGRADED
    assert decision.isolate is False
    assert decision.allow_new_tasks is False
    assert decision.allow_risk_bearing_actions is False


def test_warning_allows_safe_work_but_not_risk_bearing_actions():
    decision = evaluate_health([HealthSignal("latency_high", Severity.WARNING)])
    assert decision.state is HealthState.DEGRADED
    assert decision.allow_new_tasks is True
    assert decision.allow_risk_bearing_actions is False


def test_empty_signals_are_healthy_only_when_not_quarantined():
    decision = evaluate_health([])
    assert decision.state is HealthState.HEALTHY
    assert decision.allow_risk_bearing_actions is False
