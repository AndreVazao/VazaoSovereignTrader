from __future__ import annotations

from types import SimpleNamespace

from PC_ENGINE.core.engine import RuntimeState, SovereignEngine
from PC_ENGINE.core.execution_gate import ExecutionState
from PC_ENGINE.core.order_manager import OrderResult


class GateStub:
    def can_submit(self, **kwargs):
        return SimpleNamespace(allowed=True, state=ExecutionState.REAL_ACTIVE, reason="ok")


class UnknownOrderManager:
    def buy(self, *args, **kwargs):
        return OrderResult(False, "buy", "BTC/USDT", 0.0, 100.0, 0.0, "", "ambiguous exchange outcome: TimeoutError", 0.1, "UNKNOWN_OUTCOME")


def test_unknown_outcome_keeps_execution_intent_for_restart_reconciliation():
    engine = object.__new__(SovereignEngine)
    engine.paper = False
    engine.state = RuntimeState(status="RUNNING", mode="REAL")
    engine.state.open_positions = {}
    engine.state.execution_intents = {}
    engine.state.pending_orders = {}
    engine.execution_gate = GateStub()
    engine.order_manager = UnknownOrderManager()
    engine._persist_recovery = lambda: None
    engine.log = lambda *args, **kwargs: None
    engine._enter_safe_state = lambda *args, **kwargs: setattr(engine.state, "status", "SAFE_MODE")

    exchange = SimpleNamespace(name="TEST")
    engine._open_position(
        exchange, "BTC/USDT", 100.0, 0.1, 0.02, 0.04, "crash-window",
        execution_checks={"opportunity_ok": True, "risk_ok": True, "exchange_ok": True, "stale_ok": True},
    )

    assert engine.state.status == "SAFE_MODE"
    assert len(engine.state.execution_intents) == 1
    intent = next(iter(engine.state.execution_intents.values()))
    assert intent["client_order_id"].endswith("-buy")
    assert engine.state.pending_orders == {}
