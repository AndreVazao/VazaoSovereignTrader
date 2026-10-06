from __future__ import annotations

import json
from pathlib import Path

import PC_ENGINE.core.engine as engine_module
from PC_ENGINE.core.engine import SovereignEngine


class PaperExchange:
    name = "paper-restart"
    client = None


def _config() -> dict:
    path = Path(__file__).resolve().parents[1] / "PC_ENGINE" / "config" / "config.example.json"
    config = json.loads(path.read_text(encoding="utf-8"))
    config["owner"]["id"] = "paper-restart-owner"
    config["radar"]["enabled"] = False
    config["shared_intelligence"]["sync_enabled"] = False
    config["exchanges"] = {}
    config["engine"]["paper_starting_balance"] = 1000
    return config


def test_paper_position_survives_process_restart(tmp_path, monkeypatch):
    monkeypatch.setattr(engine_module, "DATA_DIR", tmp_path / "data")
    config = _config()
    exchange = PaperExchange()

    first = SovereignEngine(config)
    first._open_position(exchange, "BTC/USDT", 100.0, 0.01, 0.02, 0.04, "restart recovery")
    first_position = first.state.open_positions["BTC/USDT"]
    first._persist_recovery()

    second = SovereignEngine(config)
    recovered = second.state.open_positions["BTC/USDT"]

    assert recovered.exchange == first_position.exchange
    assert recovered.symbol == first_position.symbol
    assert recovered.qty == first_position.qty
    assert recovered.entry == first_position.entry
    assert recovered.stop == first_position.stop
    assert recovered.take_profit == first_position.take_profit
    assert second.state.pending_orders == {}
    assert second.state.execution_intents == {}
    assert second.state.status != "SAFE_MODE"


def test_corrupt_recovery_state_enters_safe_mode(tmp_path, monkeypatch):
    monkeypatch.setattr(engine_module, "DATA_DIR", tmp_path / "data")
    config = _config()
    state_path = tmp_path / "data" / "owners" / "paper-restart-owner" / "runtime_state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text("{broken-json", encoding="utf-8")

    engine = SovereignEngine(config)

    assert engine.state.status == "SAFE_MODE"
    assert engine.state.operational["recovery_state_corrupt"] is True
    assert engine.state.operational["recovery_error"]


def test_reconciliation_restart_restores_pending_orders_intents_and_guards(tmp_path, monkeypatch):
    monkeypatch.setattr(engine_module, "DATA_DIR", tmp_path / "data")
    config = _config()
    first = SovereignEngine(config)

    first.state.pending_orders["order-1"] = {
        "exchange": "paper-restart",
        "symbol": "BTC/USDT",
        "side": "buy",
        "requested_qty": 1.0,
        "known_filled_qty": 0.25,
        "known_fill_price": 100.0,
        "client_order_id": "cid-1",
    }
    first.state.execution_intents["intent-1"] = {
        "exchange": "paper-restart",
        "symbol": "BTC/USDT",
        "side": "buy",
        "requested_qty": 1.0,
        "client_order_id": "cid-1",
    }
    first.order_manager.last_client_order["guard-1"] = __import__("time").monotonic()

    target = first.recovery._build_payload(
        first.state.open_positions,
        first.state.pending_orders,
        first.order_manager.export_order_guards(),
        first.state.execution_intents,
        first.state.financial_account,
        first.risk.snapshot_state(),
        1,
    )
    first.recovery.prepare_reconciliation(target)

    second = SovereignEngine(config)

    assert second.state.pending_orders["order-1"]["known_filled_qty"] == 0.25
    assert second.state.execution_intents["intent-1"]["client_order_id"] == "cid-1"
    assert "guard-1" in second.order_manager.last_client_order
    assert second.state.status == "SAFE_MODE"
