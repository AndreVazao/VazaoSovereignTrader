from types import SimpleNamespace

from PC_ENGINE.core.real_mode_guard import RealModeGuard
from PC_ENGINE.core.real_readiness_service import RealReadinessService
from PC_ENGINE.core.engine import SovereignEngine


def test_readiness_target_real_requires_live_credentials(monkeypatch, tmp_path):
    monkeypatch.setenv("BINANCE_KEY", "key")
    monkeypatch.setenv("BINANCE_PRIVATE", "secret")
    service = RealReadinessService({
        "real_readiness": {
            "data_dir": str(tmp_path),
            "history_enabled": False,
        }
    })
    engine = SimpleNamespace(
        mode="PAPER",
        config={"exchanges": {"binance": {"enabled": True, "key_env": "BINANCE_KEY", "private_env": "BINANCE_PRIVATE"}}, "real_readiness": {}},
        state=SimpleNamespace(preflight={"ok": True}, watchdog={"ok": True}, open_positions={}, pending_orders={}, execution_intents={}, logs=[], account_reconciliation={}),
    )
    ok, detail = service._live_credentials_ok(engine, target_mode="REAL")
    assert ok
    assert "credentials present" in detail


def test_readiness_target_real_blocks_missing_live_credentials(monkeypatch, tmp_path):
    monkeypatch.delenv("BINANCE_KEY", raising=False)
    monkeypatch.delenv("BINANCE_PRIVATE", raising=False)
    service = RealReadinessService({"real_readiness": {"data_dir": str(tmp_path), "history_enabled": False}})
    engine = SimpleNamespace(
        mode="PAPER",
        config={"exchanges": {"binance": {"enabled": True, "key_env": "BINANCE_KEY", "private_env": "BINANCE_PRIVATE"}}},
    )
    ok, detail = service._live_credentials_ok(engine, target_mode="REAL")
    assert not ok
    assert "missing API credentials" in detail


def test_autonomous_guard_accepts_only_ready_report():
    guard = RealModeGuard({"enabled": True, "allow_real": True, "arm_seconds": 300})
    ok, _ = guard.authorize_from_readiness({"ready": False, "blockers": ["STATE_OUTCOMES"]})
    assert not ok
    ok, _ = guard.authorize_from_readiness({"ready": True, "blockers": []})
    assert ok
    ok, _ = guard.consume()
    assert ok


def test_engine_autonomous_promotion_requires_stable_paper_review():
    engine = SovereignEngine.__new__(SovereignEngine)
    engine.mode = "PAPER"
    engine.config = {"autonomous_execution": {"allow_real": True, "auto_promote_real": True}}
    engine.state = SimpleNamespace(operational={}, status="RUNNING")
    engine.real_mode_guard = RealModeGuard({"enabled": True, "allow_real": True})
    engine.real_readiness_service = SimpleNamespace(collect=lambda *args, **kwargs: {
        "ready": True,
        "status": "READY_FOR_PROTECTED_REAL_REVIEW",
        "blockers": [],
        "paper_review": {"ready": False},
    })
    engine.log = lambda *args, **kwargs: None
    assert not engine._maybe_autonomous_real_promotion()
    assert engine.mode == "PAPER"


def test_engine_autonomous_promotion_runs_only_after_stable_review():
    engine = SovereignEngine.__new__(SovereignEngine)
    engine.mode = "PAPER"
    engine.config = {"autonomous_execution": {"allow_real": True, "auto_promote_real": True}}
    engine.state = SimpleNamespace(operational={}, status="RUNNING")
    engine.real_mode_guard = RealModeGuard({"enabled": True, "allow_real": True})
    engine.real_readiness_service = SimpleNamespace(collect=lambda *args, **kwargs: {
        "ready": True,
        "status": "READY_FOR_PROTECTED_REAL_REVIEW",
        "blockers": [],
        "paper_review": {"ready": True},
    })
    engine.log = lambda *args, **kwargs: None
    engine.set_mode = lambda mode, **kwargs: setattr(engine, "mode", mode)
    engine.run_preflight = lambda: {"ok": True}
    engine.reconcile_account_state = lambda: {"ok": True}
    engine.real_operational = False
    engine._enter_real_fail_safe = lambda *args, **kwargs: None
    assert engine._maybe_autonomous_real_promotion()
    assert engine.mode == "REAL"
    assert engine.real_operational
    assert not engine.real_mode_guard.snapshot()["armed"]
