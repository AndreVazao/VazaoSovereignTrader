from __future__ import annotations

import json
from pathlib import Path

import PC_ENGINE.core.engine as engine_module
from PC_ENGINE.core.engine import SovereignEngine
from PC_ENGINE.learning.sqlite_memory import SQLiteLearningMemory


def test_engine_wires_owner_private_durable_memory_to_autonomous_research(tmp_path, monkeypatch):
    config_path = Path(__file__).resolve().parents[1] / "PC_ENGINE" / "config" / "config.example.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["owner"]["id"] = "learning-memory-integration-test"
    config["exchanges"] = {}
    config["shared_intelligence"]["sync_enabled"] = False
    monkeypatch.setattr(engine_module, "DATA_DIR", tmp_path / "runtime")

    engine = SovereignEngine(config)
    try:
        memory = engine.learning_memory
        assert isinstance(memory, SQLiteLearningMemory)
        expected_path = engine.owner_context.private_path("learning/sovereign-learning.sqlite3")
        assert Path(memory.database_path) == expected_path
        assert engine.autonomous_research.learning_memory is memory
        assert engine.state.operational["learning_memory"]["state"] == "READY"
        assert engine.state.operational["learning_memory"]["order_authority"] is False

        assert engine.autonomous_research.observe("BTC/USDT", 82, "TREND", {"paper_only": True})
        records = memory.list_records()
        assert len(records) == 1
        assert records[0].value["symbol"] == "BTC/USDT"
        assert records[0].status == "unverified"
        assert engine.close() is True
        assert engine.learning_memory is None
        assert engine.state.operational["learning_memory"]["state"] == "CLOSED"
        assert engine.close() is True
        engine.start()
        assert engine.state.status != "RUNNING"
    finally:
        if engine.learning_memory is not None:
            engine.close()


def test_engine_can_disable_durable_learning_memory(tmp_path, monkeypatch):
    config_path = Path(__file__).resolve().parents[1] / "PC_ENGINE" / "config" / "config.example.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["owner"]["id"] = "learning-memory-disabled-test"
    config["exchanges"] = {}
    config["shared_intelligence"]["sync_enabled"] = False
    config["learning_memory"] = {"enabled": False}
    monkeypatch.setattr(engine_module, "DATA_DIR", tmp_path / "runtime")

    engine = SovereignEngine(config)
    assert engine.learning_memory is None
    assert engine.autonomous_research.learning_memory is None
    assert engine.state.operational["learning_memory"]["state"] == "DISABLED"
    assert engine.close() is True