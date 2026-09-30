# Path: tests/test_execution_gate.py
from PC_ENGINE.core.execution_gate import ExecutionGate, ExecutionState


def test_first_real_activation_requires_human_authorization():
    gate = ExecutionGate()
    decision = gate.activate_real()
    assert not decision.allowed
    assert decision.state == ExecutionState.REAL_AUTH_REQUIRED


def test_human_authorization_allows_real_activation():
    gate = ExecutionGate()
    gate.human_authorize()
    decision = gate.activate_real()
    assert decision.allowed
    assert decision.state == ExecutionState.REAL_ACTIVE


def test_fail_safe_then_recovery_is_automatic_but_gated():
    gate = ExecutionGate()
    gate.human_authorize()
    gate.activate_real()
    gate.fail_safe("exchange timing failure")
    decision = gate.evaluate_recovery(readiness_ok=True, reconciliation_ok=True, timing_ok=True)
    assert decision.allowed
    assert decision.state == ExecutionState.REAL_RECOVERY_ELIGIBLE
    assert gate.activate_real().state == ExecutionState.REAL_ACTIVE


def test_recovery_cannot_create_first_authorization():
    gate = ExecutionGate()
    decision = gate.evaluate_recovery(readiness_ok=True, reconciliation_ok=True, timing_ok=True)
    assert not decision.allowed
    assert decision.state == ExecutionState.REAL_AUTH_REQUIRED


def test_submission_is_fail_closed():
    gate = ExecutionGate()
    gate.human_authorize()
    gate.activate_real()
    assert not gate.can_submit(opportunity_ok=True, risk_ok=False, exchange_ok=True, stale_ok=True).allowed
    assert gate.can_submit(opportunity_ok=True, risk_ok=True, exchange_ok=True, stale_ok=True).allowed
