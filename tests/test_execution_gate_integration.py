# Path: tests/test_execution_gate_integration.py
from types import SimpleNamespace

import pytest

from PC_ENGINE.core.engine import SovereignEngine
from PC_ENGINE.core.execution_gate import ExecutionGate, ExecutionState
from PC_ENGINE.core.real_mode_guard import RealModeGuard


def test_engine_rejects_real_mode_without_guard_human_authorization():
    engine = SovereignEngine.__new__(SovereignEngine)
    engine.config = {"autonomous_execution": {"allow_real": True}}
    engine.state = SimpleNamespace(status="OFF", mode="PAPER")
    engine.paper_collector = None
    engine.real_mode_guard = RealModeGuard({"enabled": True, "allow_real": True})
    engine.execution_gate = ExecutionGate()
    with pytest.raises(RuntimeError, match="human authorization"):
        engine.set_mode("REAL", real_authorized=True)


def test_real_order_submission_is_blocked_when_execution_gate_not_active():
    engine = SovereignEngine.__new__(SovereignEngine)
    engine.paper = False
    engine.mode = "REAL"
    engine.execution_gate = ExecutionGate()
    engine.exchanges = {"binance": SimpleNamespace(name="binance")}
    logged = []
    failsafe = []
    engine.log = lambda message, data=None: logged.append((message, data))
    engine._enter_real_fail_safe = lambda reason, data=None: failsafe.append((reason, data))

    engine._open_position(
        exchange=engine.exchanges["binance"],
        symbol="BTC/USDT",
        price=60000.0,
        qty=0.001,
        stop_pct=0.01,
        tp_pct=0.02,
        reason="test",
    )

    assert engine.execution_gate.state == ExecutionState.PAPER
    assert any(row[0] == "EXECUTION_GATE_BLOCKED_ORDER" for row in logged)
    assert failsafe and failsafe[0][0] == "execution_gate_order_blocked"


def test_real_order_gate_requires_all_runtime_checks():
    gate = ExecutionGate()
    gate.human_authorize()
    gate.activate_real()

    decision = gate.can_submit(
        opportunity_ok=True,
        risk_ok=True,
        exchange_ok=True,
        stale_ok=False,
    )
    assert not decision.allowed
    assert decision.state == ExecutionState.REAL_ACTIVE
