from __future__ import annotations

import json
from pathlib import Path

import PC_ENGINE.core.engine as engine_module
from PC_ENGINE.core.engine import SovereignEngine


class ControlledRecoveryExchange:
    name = "controlled-recovery"

    def __init__(self):
        self.lookup_calls = 0
        self.fetch_calls = 0
        self.orders = {}

    def fetch_open_orders(self):
        return []

    def fetch_order_by_client_order_id(self, client_order_id, symbol):
        self.lookup_calls += 1
        order = self.orders.get(client_order_id)
        if order is None:
            raise LookupError("not found")
        return dict(order)

    def fetch_order(self, order_id, symbol):
        self.fetch_calls += 1
        for order in self.orders.values():
            if str(order.get("id")) == str(order_id):
                return dict(order)
        raise LookupError("not found")


class PaperExchange:
    name = "paper-restart"
    client = None


def _config() -> dict:
    path = Path(__file__).resolve().parents[1] / "PC_ENGINE" / "config" / "config.example.json"
    config = json.loads(path.read_text(encoding="utf-8"))
    config["owner"]["id"] = "controlled-recovery-owner"
    config["radar"]["enabled"] = False
    config["shared_intelligence"]["sync_enabled"] = False
    config["exchanges"] = {}
    config["engine"]["paper_starting_balance"] = 1000
    return config


def _force_controlled_real(engine: SovereignEngine, exchange: ControlledRecoveryExchange) -> None:
    engine.paper = False
    engine.mode = "REAL"
    engine.real_operational = False
    engine.state.mode = "REAL"
    engine.exchanges = {exchange.name: exchange}
    engine._main_exchange = lambda: exchange


def test_controlled_unknown_intent_survives_restart_and_resolves_exact_identity(tmp_path, monkeypatch):
    monkeypatch.setattr(engine_module, "DATA_DIR", tmp_path / "data")
    config = _config()

    first = SovereignEngine(config)
    first.state.status = "SAFE_MODE"
    first.state.execution_intents["intent-crash-1"] = {
        "exchange": "controlled-recovery",
        "symbol": "BTC/USDT",
        "side": "buy",
        "requested_qty": 0.25,
        "reference_price": 100.0,
        "client_order_id": "vzt-crash-stable-1",
        "stop_pct": 0.02,
        "take_profit_pct": 0.04,
        "created_ts": 1000.0,
        "reason": "controlled crash-window",
    }
    first._persist_recovery()

    # Simulated process death: create a fresh engine from durable state.
    exchange = ControlledRecoveryExchange()
    exchange.orders["vzt-crash-stable-1"] = {
        "id": "venue-order-1",
        "symbol": "BTC/USDT",
        "side": "buy",
        "status": "closed",
        "amount": 0.25,
        "filled": 0.25,
        "average": 101.0,
        "price": 101.0,
        "cost": 25.25,
        "clientOrderId": "vzt-crash-stable-1",
    }

    second = SovereignEngine(config)
    _force_controlled_real(second, exchange)
    assert "intent-crash-1" in second.state.execution_intents
    assert second.state.status == "SAFE_MODE"

    second._recover_unresolved_execution_intents()

    assert exchange.lookup_calls == 1
    assert "intent-crash-1" not in second.state.execution_intents
    assert "venue-order-1" in second.state.pending_orders
    assert second.state.pending_orders["venue-order-1"]["client_order_id"] == "vzt-crash-stable-1"
    assert second.state.pending_orders["venue-order-1"]["known_filled_qty"] == 0.0

    second._reconcile_pending_orders()

    assert second.state.status == "SAFE_MODE"
    assert second.state.pending_orders == {}
    assert second.state.execution_intents == {}
    assert second.state.open_positions["BTC/USDT"].qty == 0.25
    assert second.state.open_positions["BTC/USDT"].entry == 101.0
    assert second.state.financial_account["base_flow"]["BTC"] == 0.25
    assert second.state.financial_account["quote_flow"] == -25.25
    assert exchange.fetch_calls == 1


def test_restart_replay_is_ledger_idempotent_and_does_not_retry_external_order(tmp_path, monkeypatch):
    monkeypatch.setattr(engine_module, "DATA_DIR", tmp_path / "data")
    config = _config()

    first = SovereignEngine(config)
    first.state.status = "SAFE_MODE"
    first.state.execution_intents["intent-crash-2"] = {
        "exchange": "controlled-recovery",
        "symbol": "BTC/USDT",
        "side": "buy",
        "requested_qty": 0.10,
        "reference_price": 200.0,
        "client_order_id": "vzt-crash-stable-2",
        "stop_pct": 0.02,
        "take_profit_pct": 0.04,
        "created_ts": 1001.0,
        "reason": "controlled crash-window",
    }
    first._persist_recovery()

    exchange = ControlledRecoveryExchange()
    exchange.orders["vzt-crash-stable-2"] = {
        "id": "venue-order-2",
        "symbol": "BTC/USDT",
        "side": "buy",
        "status": "closed",
        "amount": 0.10,
        "filled": 0.10,
        "average": 201.0,
        "price": 201.0,
        "cost": 20.10,
        "clientOrderId": "vzt-crash-stable-2",
    }

    second = SovereignEngine(config)
    _force_controlled_real(second, exchange)
    second._recover_unresolved_execution_intents()
    second._reconcile_pending_orders()

    # Replay from the same durable snapshot must not submit another order.
    third = SovereignEngine(config)
    _force_controlled_real(third, exchange)
    third._recover_unresolved_execution_intents()
    third._reconcile_pending_orders()

    assert exchange.lookup_calls == 1
    assert exchange.fetch_calls == 1
    assert third.state.open_positions["BTC/USDT"].qty == 0.10
    assert third.state.execution_intents == {}
    assert third.state.pending_orders == {}
    assert len(third.ledger.read_trades()) == 0
