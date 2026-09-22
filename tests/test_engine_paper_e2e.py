from __future__ import annotations

import json
from pathlib import Path

import PC_ENGINE.core.engine as engine_module
from PC_ENGINE.core.engine import SovereignEngine


class PaperExchange:
    name = "paper-e2e"

    client = None


def test_engine_paper_round_trip_isolated_and_persisted(tmp_path, monkeypatch):
    config_path = Path(__file__).resolve().parents[1] / "PC_ENGINE" / "config" / "config.example.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["owner"]["id"] = "paper-e2e-owner"
    config["radar"]["enabled"] = False
    config["shared_intelligence"]["sync_enabled"] = False
    config["exchanges"] = {}
    config["engine"]["paper_starting_balance"] = 1000

    monkeypatch.setattr(engine_module, "DATA_DIR", tmp_path / "data")
    engine = SovereignEngine(config)
    exchange = PaperExchange()

    engine._open_position(
        exchange,
        "BTC/USDT",
        100.0,
        0.01,
        0.02,
        0.04,
        "deterministic paper e2e",
    )

    position = engine.state.open_positions["BTC/USDT"]
    assert position.qty == 0.01
    assert position.entry > 100.0
    assert position.stop < position.entry < position.take_profit
    assert engine.state.execution_intents == {}
    assert engine.state.pending_orders == {}

    engine._close_position(
        exchange,
        position,
        105.0,
        "deterministic paper e2e close",
    )

    assert engine.state.open_positions == {}
    assert engine.state.execution_intents == {}
    assert engine.state.pending_orders == {}

    trades_path = tmp_path / "data" / "owners" / "paper-e2e-owner" / "logs" / "trades.jsonl"
    assert trades_path.exists()
    trades = [json.loads(line) for line in trades_path.read_text(encoding="utf-8").splitlines() if line]
    assert len(trades) == 1
    assert trades[0]["symbol"] == "BTC/USDT"
    assert trades[0]["qty"] == 0.01
    assert trades[0]["fees"] > 0
    assert engine.state.financial_account["base_flow"]["BTC"] == 0.0
