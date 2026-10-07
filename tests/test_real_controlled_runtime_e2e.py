from __future__ import annotations

from types import SimpleNamespace

from PC_ENGINE.core.engine import RuntimeState, SovereignEngine
from PC_ENGINE.core.execution_gate import ExecutionGate, ExecutionState
from PC_ENGINE.core.order_manager import OrderManager


class ControlledRules:
    def validate_order(self, exchange, symbol, qty, price):
        return True, "", float(qty)


class ControlledAdapter:
    name = "controlled-test-adapter"

    def __init__(self):
        self.calls = []
        self.counter = 0

    def market_buy_with_client_order_id(self, symbol, qty, client_order_id):
        self.counter += 1
        order_id = f"controlled-buy-{self.counter}"
        self.calls.append(("buy", symbol, float(qty), client_order_id))
        return {"id": order_id, "status": "closed", "filled": float(qty), "average": 100.0, "price": 100.0,
                "cost": float(qty) * 100.0, "fee": {"cost": 0.1, "currency": "USDT"},
                "symbol": symbol, "side": "buy", "clientOrderId": client_order_id}

    def market_sell_with_client_order_id(self, symbol, qty, client_order_id):
        self.counter += 1
        order_id = f"controlled-sell-{self.counter}"
        self.calls.append(("sell", symbol, float(qty), client_order_id))
        return {"id": order_id, "status": "closed", "filled": float(qty), "average": 105.0, "price": 105.0,
                "cost": float(qty) * 105.0, "fee": {"cost": 0.1, "currency": "USDT"},
                "symbol": symbol, "side": "sell", "clientOrderId": client_order_id}


def _engine_for_controlled_runtime():
    engine = object.__new__(SovereignEngine)
    engine.mode = "REAL"
    engine.paper = False
    engine.real_operational = True
    engine.state = RuntimeState(mode="REAL")
    engine.state.status = "RUNNING"
    engine.execution_gate = ExecutionGate()
    engine.execution_gate.human_authorize()
    engine.execution_gate.activate_real()
    assert engine.execution_gate.state is ExecutionState.REAL_ACTIVE
    engine.rules = ControlledRules()
    engine.order_manager = OrderManager(engine.rules, SimpleNamespace(), execution_authorizer=engine._authorize_order_side_effect)
    engine.config = {"reconciliation": {"financial_relative_tolerance": 0.002}}
    engine.exchanges = {}
    engine.log = lambda *args, **kwargs: None
    engine._persist_recovery = lambda: None
    engine._record_financial_fill = lambda *args, **kwargs: None
    engine._enter_real_fail_safe = lambda reason, data=None: setattr(engine.state, "status", "SAFE_MODE")
    engine._enter_safe_state = lambda reason: setattr(engine.state, "status", "SAFE_MODE")
    return engine


def test_controlled_real_runtime_end_to_end_order_chain():
    engine = _engine_for_controlled_runtime()
    exchange = ControlledAdapter()
    engine.exchanges[exchange.name] = exchange
    engine._open_position(exchange, "BTC/USDT", 100.0, 0.01, 0.02, 0.04, "controlled end-to-end",
                          execution_checks={"opportunity_ok": True, "risk_ok": True, "exchange_ok": True, "stale_ok": True})
    assert engine.state.status == "RUNNING"
    assert engine.state.pending_orders == {}
    assert engine.state.execution_intents == {}
    assert engine.state.open_positions["BTC/USDT"].qty == 0.01
    assert exchange.calls[0][0] == "buy" and exchange.calls[0][3]
    position = engine.state.open_positions["BTC/USDT"]
    engine._close_position(exchange, position, 105.0, "controlled end-to-end close",
                           execution_checks={"opportunity_ok": True, "risk_ok": True, "exchange_ok": True, "stale_ok": True})
    assert engine.state.status == "RUNNING"
    assert engine.state.open_positions == {}
    assert engine.state.pending_orders == {}
    assert engine.state.execution_intents == {}
    assert [call[0] for call in exchange.calls] == ["buy", "sell"]


def test_controlled_real_runtime_cannot_submit_without_active_gate():
    engine = _engine_for_controlled_runtime()
    engine.execution_gate.reset_to_paper()
    exchange = ControlledAdapter()
    engine.exchanges[exchange.name] = exchange
    engine._open_position(exchange, "BTC/USDT", 100.0, 0.01, 0.02, 0.04, "blocked controlled order",
                          execution_checks={"opportunity_ok": True, "risk_ok": True, "exchange_ok": True, "stale_ok": True})
    assert exchange.calls == []
    assert engine.state.status == "SAFE_MODE"
    assert engine.state.execution_intents == {}
