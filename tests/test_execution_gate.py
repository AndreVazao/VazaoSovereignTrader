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


def test_fail_safe_blocks_new_submissions_until_recovery_gates_pass():
    gate = ExecutionGate()
    gate.human_authorize()
    gate.activate_real()
    gate.fail_safe("stale market data")

    blocked = gate.can_submit(
        opportunity_ok=True, risk_ok=True, exchange_ok=True, stale_ok=True
    )
    assert not blocked.allowed
    assert blocked.state == ExecutionState.SAFEGUARD_PAPER

    recovery = gate.evaluate_recovery(
        readiness_ok=True, reconciliation_ok=False, timing_ok=True
    )
    assert not recovery.allowed
    assert recovery.state == ExecutionState.SAFEGUARD_PAPER
    assert not gate.can_submit(
        opportunity_ok=True, risk_ok=True, exchange_ok=True, stale_ok=True
    ).allowed


def test_recovery_rejects_each_missing_gate():
    for readiness_ok, reconciliation_ok, timing_ok in (
        (False, True, True),
        (True, False, True),
        (True, True, False),
    ):
        gate = ExecutionGate()
        gate.human_authorize()
        gate.activate_real()
        gate.fail_safe("injected fault")

        decision = gate.evaluate_recovery(
            readiness_ok=readiness_ok,
            reconciliation_ok=reconciliation_ok,
            timing_ok=timing_ok,
        )
        assert not decision.allowed
        assert decision.state == ExecutionState.SAFEGUARD_PAPER
