from __future__ import annotations

import json
from pathlib import Path

import PC_ENGINE.core.engine as engine_module
from PC_ENGINE.core.engine import Position, SovereignEngine


class StagedExchange:
    name = "staged-recovery"
    client = None

    def __init__(self, raw):
        self.raw = dict(raw)

    def fetch_order(self, order_id, symbol):
        return dict(self.raw)


def _config() -> dict:
    path = Path(__file__).resolve().parents[1] / "PC_ENGINE" / "config" / "config.example.json"
    config = json.loads(path.read_text(encoding="utf-8"))
    config["owner"]["id"] = "partial-fill-restart-owner"
    config["radar"]["enabled"] = False
    config["shared_intelligence"]["sync_enabled"] = False
    config["exchanges"] = {}
    config["engine"]["paper_starting_balance"] = 1000
    return config


def _pending_order() -> dict:
    return {
        "exchange": "staged-recovery",
        "symbol": "BTC/USDT",
        "side": "buy",
        "requested_qty": 1.0,
        "known_filled_qty": 0.0,
        "known_fill_price": 100.0,
        "known_quote_notional": 0.0,
        "known_fee": 0.0,
        "created_ts": 1.0,
        "client_order_id": "client-partial-1",
        "stop_pct": 0.02,
        "take_profit_pct": 0.04,
        "reason": "partial fill recovery",
    }


def _exchange_for(raw):
    exchange = StagedExchange(raw)

    def resolve(_item):
        return exchange

    return exchange, resolve


def test_partial_fill_crash_restart_then_terminal_fill_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(engine_module, "DATA_DIR", tmp_path / "data")
    config = _config()

    first = SovereignEngine(config)
    first.state.pending_orders["order-1"] = _pending_order()
    first._persist_recovery()

    first_raw = {
        "id": "order-1",
        "symbol": "BTC/USDT",
        "side": "buy",
        "status": "open",
        "filled": 0.4,
        "average": 100.0,
        "cost": 40.0,
        "fee": {"cost": 0.04, "currency": "USDT"},
        "clientOrderId": "client-partial-1",
    }
    first_exchange, first_resolver = _exchange_for(first_raw)
    monkeypatch.setattr(first, "_exchange_for_pending_order", first_resolver)
    first._reconcile_pending_orders()

    assert first.state.pending_orders["order-1"]["known_filled_qty"] == 0.4
    assert first.state.pending_orders["order-1"]["known_quote_notional"] == 40.0
    assert first.state.pending_orders["order-1"]["known_fee"] == 0.04
    assert first.state.open_positions["BTC/USDT"].qty == 0.4
    assert first.state.open_positions["BTC/USDT"].entry_fee == 0.04

    second = SovereignEngine(config)
    assert second.state.pending_orders["order-1"]["known_filled_qty"] == 0.4
    assert second.state.open_positions["BTC/USDT"].qty == 0.4

    second_raw = {
        "id": "order-1",
        "symbol": "BTC/USDT",
        "side": "buy",
        "status": "closed",
        "filled": 1.0,
        "average": 101.0,
        "cost": 101.0,
        "fee": {"cost": 0.10, "currency": "USDT"},
        "clientOrderId": "client-partial-1",
    }
    second_exchange, second_resolver = _exchange_for(second_raw)
    monkeypatch.setattr(second, "_exchange_for_pending_order", second_resolver)
    second._reconcile_pending_orders()

    position = second.state.open_positions["BTC/USDT"]
    assert position.qty == 1.0
    assert position.entry == 100.6
    assert position.entry_fee == 0.10
    assert second.state.pending_orders == {}

    # A repeated reconciliation after the terminal fill cannot apply the
    # same 0.6 delta again because the durable pending order is gone.
    second._reconcile_pending_orders()
    assert second.state.open_positions["BTC/USDT"].qty == 1.0
    assert second.state.open_positions["BTC/USDT"].entry == 100.6
    assert second.state.open_positions["BTC/USDT"].entry_fee == 0.10
