import json
from pathlib import Path

from PC_ENGINE.core.engine import SovereignEngine
from PC_ENGINE.core.real_mode_guard import RealModeGuard


def test_engine_initializes_real_mode_guard_from_config(tmp_path):
    config = json.loads(Path("PC_ENGINE/config/config.example.json").read_text(encoding="utf-8"))
    config["owner"]["id"] = "test-owner"
    config["engine"]["paper_starting_balance"] = 1000
    config["real_mode_guard"] = {"enabled": True, "allow_real": True, "arm_seconds": 300}
    config["real_readiness"]["data_dir"] = str(tmp_path / "radar")
    config["real_readiness"]["history_path"] = str(tmp_path / "radar" / "readiness_history.jsonl")
    config["paper"]["reconciliation_path"] = str(tmp_path / "paper" / "reconciliation.json")
    config["evidence"]["ledger_path"] = str(tmp_path / "radar" / "evidence_ledger.jsonl")

    engine = SovereignEngine(config)

    assert isinstance(engine.real_mode_guard, RealModeGuard)
    snapshot = engine.real_mode_guard.snapshot()
    assert snapshot["armed"] is False
    assert engine.real_mode_guard.allow_real is True


def test_engine_startup_still_normalizes_configured_real_to_paper(tmp_path):
    config = json.loads(Path("PC_ENGINE/config/config.example.json").read_text(encoding="utf-8"))
    config["mode"] = "REAL"
    config["owner"]["id"] = "test-owner"
    config["real_readiness"]["data_dir"] = str(tmp_path / "radar")
    config["real_readiness"]["history_path"] = str(tmp_path / "radar" / "readiness_history.jsonl")
    engine = SovereignEngine(config)

    assert engine.mode == "PAPER"
    assert engine.paper is True
    assert engine.real_mode_guard.snapshot()["armed"] is False
