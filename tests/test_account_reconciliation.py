from __future__ import annotations

from PC_ENGINE.core.engine import Position, RuntimeState, SovereignEngine


class FakeExchange:
    name = "fake"

    def __init__(self, balance, open_orders):
        self.balance = balance
        self.open_orders = open_orders

    def fetch_balance(self):
        return self.balance

    def fetch_open_orders(self):
        return self.open_orders


def make_engine(balance, open_orders, positions):
    engine = object.__new__(SovereignEngine)
    engine.mode = "REAL"
    engine.paper = False
    engine.config = {"engine": {"quote_currency": "USDT"}}
    engine.state = RuntimeState(mode="REAL", open_positions=positions)
    engine.exchanges = {"fake": FakeExchange(balance, open_orders)}
    engine.ledger = type("Ledger", (), {"event": lambda self, *args, **kwargs: None})()
    return engine


def test_account_reconciliation_matches_local_positions_and_no_open_orders():
    positions = {"BTC/USDT": Position("fake", "BTC/USDT", 100.0, 0.5, 90.0, 120.0, 1.0)}
    engine = make_engine({"total": {"BTC": 0.5, "USDT": 1000.0}}, [], positions)
    result = engine.reconcile_account_state()
    assert result["ok"] is True
    assert result["status"] == "MATCH"


def test_account_reconciliation_blocks_position_mismatch():
    positions = {"BTC/USDT": Position("fake", "BTC/USDT", 100.0, 0.5, 90.0, 120.0, 1.0)}
    engine = make_engine({"total": {"BTC": 0.2, "USDT": 1000.0}}, [], positions)
    result = engine.reconcile_account_state()
    assert result["ok"] is False
    assert result["status"] == "BLOCKED"
    assert engine.state.status == "SAFE_MODE"


def test_account_reconciliation_blocks_unexpected_assets_and_open_orders():
    engine = make_engine(
        {"total": {"ETH": 1.0, "USDT": 1000.0}},
        [{"id": "open-1", "symbol": "BTC/USDT"}],
        {},
    )
    result = engine.reconcile_account_state()
    assert result["ok"] is False
    assert result["open_orders"] == 1
    assert result["unexpected_assets"][0]["asset"] == "ETH"


def test_account_reconciliation_safe_mode_persists_across_restart(tmp_path, monkeypatch):
    import json
    from pathlib import Path
    import PC_ENGINE.core.engine as engine_module

    monkeypatch.setattr(engine_module, "DATA_DIR", tmp_path / "data")
    config_path = Path(__file__).resolve().parents[1] / "PC_ENGINE" / "config" / "config.example.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["owner"]["id"] = "reconciliation-safe-mode-owner"
    config["radar"]["enabled"] = False
    config["shared_intelligence"]["sync_enabled"] = False
    config["exchanges"] = {}

    first = SovereignEngine(config)
    first.mode = "REAL"
    first.paper = False
    first.state.mode = "REAL"
    first.exchanges = {"fake": FakeExchange({"total": {"BTC": 0.2, "USDT": 1000.0}}, [])}
    first.state.open_positions = {
        "BTC/USDT": Position("fake", "BTC/USDT", 100.0, 0.5, 90.0, 120.0, 1.0)
    }

    blocked = first.reconcile_account_state()
    assert blocked["status"] == "BLOCKED"
    assert first.state.status == "SAFE_MODE"
    assert first.state.open_positions["BTC/USDT"].qty == 0.5
    assert first.recovery.load_state()["runtime_status"] == "SAFE_MODE"

    second = SovereignEngine(config)
    assert second.state.status == "SAFE_MODE"
    assert second.state.operational["persisted_safe_mode"] is True
    assert second.state.open_positions["BTC/USDT"].qty == 0.5

    repeated = first.reconcile_account_state()
    assert repeated["status"] == "BLOCKED"
    assert first.state.status == "SAFE_MODE"
    assert first.state.open_positions["BTC/USDT"].qty == 0.5

def test_safe_mode_blocks_start_after_multiple_restarts(tmp_path, monkeypatch):
    import json
    from pathlib import Path
    import PC_ENGINE.core.engine as engine_module

    monkeypatch.setattr(engine_module, "DATA_DIR", tmp_path / "data")
    config_path = Path(__file__).resolve().parents[1] / "PC_ENGINE" / "config" / "config.example.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["owner"]["id"] = "safe-mode-restart-owner"
    config["radar"]["enabled"] = False
    config["shared_intelligence"]["sync_enabled"] = False
    config["exchanges"] = {}

    first = SovereignEngine(config)
    first.state.status = "SAFE_MODE"
    first._persist_recovery()

    second = SovereignEngine(config)
    assert second.state.status == "SAFE_MODE"
    second.start()
    assert second.state.status == "SAFE_MODE"

    third = SovereignEngine(config)
    assert third.state.status == "SAFE_MODE"


def test_safe_mode_requires_explicit_recovery_evidence(tmp_path, monkeypatch):
    import json
    from pathlib import Path
    import PC_ENGINE.core.engine as engine_module

    monkeypatch.setattr(engine_module, "DATA_DIR", tmp_path / "data")
    config_path = Path(__file__).resolve().parents[1] / "PC_ENGINE" / "config" / "config.example.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["owner"]["id"] = "safe-mode-explicit-recovery-owner"
    config["radar"]["enabled"] = False
    config["shared_intelligence"]["sync_enabled"] = False
    config["exchanges"] = {}

    engine = SovereignEngine(config)
    engine.state.status = "SAFE_MODE"
    engine._persist_recovery()

    blocked = engine.recover_from_safe_mode(human_confirmation="wrong")
    assert blocked["ok"] is False
    assert blocked["reason"] == "human_confirmation_required"
    assert engine.state.status == "SAFE_MODE"

    import time
    engine.run_preflight = lambda: {"ok": True}
    engine.real_readiness_service.collect = lambda *args, **kwargs: {
        "ready": True,
        "status": "READY",
        "blockers": [],
        "collected_at_ms": int(time.time() * 1000),
        "paper_review": {"ready": True},
        "websocket_timing": {
            "required": False,
            "fresh": True,
            "eligible_for_economic_interpretation": True,
        },
    }

    recovered = engine.recover_from_safe_mode(human_confirmation="RECUPERAR SAFE MODE")
    assert recovered["ok"] is True
    assert recovered["evidence"]["preflight_ok"] is True
    assert recovered["evidence"]["readiness_ok"] is True
    assert recovered["evidence"]["reconciliation_ok"] is True
    assert recovered["evidence"]["timing_ok"] is True
    assert recovered["evidence"]["fresh"] is True
    assert engine.state.status == "OFF"
    assert engine.recovery.load_state()["runtime_status"] == "OFF"

    restarted = SovereignEngine(config)
    assert restarted.state.status != "SAFE_MODE"


def test_safe_mode_blocks_resume_without_explicit_recovery(tmp_path, monkeypatch):
    import json
    from pathlib import Path
    import PC_ENGINE.core.engine as engine_module

    monkeypatch.setattr(engine_module, "DATA_DIR", tmp_path / "data")
    config_path = Path(__file__).resolve().parents[1] / "PC_ENGINE" / "config" / "config.example.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["owner"]["id"] = "safe-mode-resume-owner"
    config["radar"]["enabled"] = False
    config["shared_intelligence"]["sync_enabled"] = False
    config["exchanges"] = {}

    engine = SovereignEngine(config)
    engine.state.status = "SAFE_MODE"
    assert engine.pause(False) is False
    assert engine.state.status == "SAFE_MODE"



def test_safe_mode_stop_does_not_clear_safety_latch(tmp_path, monkeypatch):
    import json
    from pathlib import Path
    import PC_ENGINE.core.engine as engine_module

    monkeypatch.setattr(engine_module, "DATA_DIR", tmp_path / "data")
    config_path = Path(__file__).resolve().parents[1] / "PC_ENGINE" / "config" / "config.example.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["owner"]["id"] = "safe-mode-stop-owner"
    config["radar"]["enabled"] = False
    config["shared_intelligence"]["sync_enabled"] = False
    config["exchanges"] = {}

    engine = SovereignEngine(config)
    engine.state.status = "SAFE_MODE"
    engine._persist_recovery()

    engine.stop()

    assert engine.state.status == "SAFE_MODE"
    assert engine.recovery.load_state()["runtime_status"] == "SAFE_MODE"
