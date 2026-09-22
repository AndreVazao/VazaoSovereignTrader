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
