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


def test_autonomous_guard_requires_human_authorization_and_ready_report():
    guard = RealModeGuard({"enabled": True, "allow_real": True, "arm_seconds": 300})
    ok, _ = guard.authorize_from_readiness({"ready": True, "blockers": []})
    assert not ok
    assert "initial human REAL authorization required" in guard.state.last_reason
    ok, _ = guard.arm("EU ACEITO O RISCO")
    assert ok
    ok, _ = guard.authorize_from_readiness({"ready": False, "blockers": ["STATE_OUTCOMES"]})
    assert not ok
    ok, _ = guard.authorize_from_readiness({"ready": True, "blockers": []})
    assert ok
    ok, _ = guard.consume()
    assert ok


def test_engine_autonomous_promotion_requires_stable_paper_review():
    engine = SovereignEngine.__new__(SovereignEngine)
    engine.mode = "PAPER"
    engine.config = {"autonomous_execution": {"enabled": True, "allow_real": True, "auto_promote_real": True}}
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
    engine.config = {"autonomous_execution": {"enabled": True, "allow_real": True, "auto_promote_real": True}}
    engine.state = SimpleNamespace(operational={}, status="RUNNING")
    engine.real_mode_guard = RealModeGuard({"enabled": True, "allow_real": True})
    engine.real_mode_guard.arm("EU ACEITO O RISCO")
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


def test_engine_autonomous_promotion_stays_paper_when_autonomy_disabled():
    engine = SovereignEngine.__new__(SovereignEngine)
    engine.mode = "PAPER"
    engine.config = {"autonomous_execution": {"enabled": False, "allow_real": True, "auto_promote_real": True}}
    engine.state = SimpleNamespace(operational={}, status="RUNNING")
    engine.real_mode_guard = RealModeGuard({"enabled": True, "allow_real": True})
    engine.real_readiness_service = SimpleNamespace(collect=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("readiness must not run when autonomy is disabled")))
    engine.log = lambda *args, **kwargs: None
    assert not engine._maybe_autonomous_real_promotion()
    assert engine.mode == "PAPER"


def test_engine_readiness_error_replaces_stale_ready_snapshot():
    engine = SovereignEngine.__new__(SovereignEngine)
    engine.mode = "PAPER"
    engine.config = {"autonomous_execution": {"enabled": True, "allow_real": True, "auto_promote_real": True}}
    engine.state = SimpleNamespace(operational={"real_readiness": {"ready": True, "status": "READY"}}, status="RUNNING")
    engine.real_mode_guard = RealModeGuard({"enabled": True, "allow_real": True})
    engine.real_readiness_service = SimpleNamespace(collect=lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("temporary evidence store failure")))
    engine.log = lambda *args, **kwargs: None
    assert not engine._maybe_autonomous_real_promotion()
    assert engine.mode == "PAPER"
    report = engine.state.operational["real_readiness"]
    assert report["ready"] is False
    assert report["status"] == "READINESS_EVALUATION_FAILED"
    assert "readiness_evaluation_failed" in report["blockers"]


def test_engine_autonomous_promotion_fails_safe_when_preflight_fails():
    engine = SovereignEngine.__new__(SovereignEngine)
    engine.mode = "PAPER"
    engine.config = {"autonomous_execution": {"enabled": True, "allow_real": True, "auto_promote_real": True}}
    engine.state = SimpleNamespace(operational={}, status="RUNNING", mode="PAPER")
    engine.real_mode_guard = RealModeGuard({"enabled": True, "allow_real": True})
    engine.real_mode_guard.arm("EU ACEITO O RISCO")
    engine.real_readiness_service = SimpleNamespace(collect=lambda *args, **kwargs: {
        "ready": True,
        "status": "READY_FOR_PROTECTED_REAL_REVIEW",
        "blockers": [],
        "paper_review": {"ready": True},
    })
    engine.log = lambda *args, **kwargs: None
    engine.set_mode = lambda mode, **kwargs: (setattr(engine, "mode", mode), setattr(engine.state, "mode", mode))
    engine.run_preflight = lambda: {"ok": False, "errors": ["credentials/preflight failure"]}
    engine.reconcile_account_state = lambda: {"ok": True}
    engine.real_operational = False
    fail_safe_calls = []
    def fail_safe(reason, data=None):
        fail_safe_calls.append((reason, data))
        engine.mode = "PAPER"
        engine.state.mode = "PAPER"
        engine.real_operational = False
        engine.state.status = "SAFE_MODE"
        engine.real_mode_guard.disarm(reason)
    engine._enter_real_fail_safe = fail_safe

    assert not engine._maybe_autonomous_real_promotion()
    assert engine.mode == "PAPER"
    assert engine.state.mode == "PAPER"
    assert not engine.real_operational
    assert engine.state.status == "SAFE_MODE"
    assert fail_safe_calls
    assert fail_safe_calls[0][0] == "autonomous_real_preflight_failed"


def test_engine_autonomous_promotion_fails_safe_when_reconciliation_fails():
    engine = SovereignEngine.__new__(SovereignEngine)
    engine.mode = "PAPER"
    engine.config = {"autonomous_execution": {"enabled": True, "allow_real": True, "auto_promote_real": True}}
    engine.state = SimpleNamespace(operational={}, status="RUNNING", mode="PAPER")
    engine.real_mode_guard = RealModeGuard({"enabled": True, "allow_real": True})
    engine.real_mode_guard.arm("EU ACEITO O RISCO")
    engine.real_readiness_service = SimpleNamespace(collect=lambda *args, **kwargs: {
        "ready": True,
        "status": "READY_FOR_PROTECTED_REAL_REVIEW",
        "blockers": [],
        "paper_review": {"ready": True},
    })
    engine.log = lambda *args, **kwargs: None
    engine.set_mode = lambda mode, **kwargs: (setattr(engine, "mode", mode), setattr(engine.state, "mode", mode))
    engine.run_preflight = lambda: {"ok": True}
    engine.reconcile_account_state = lambda: {"ok": False, "reason": "account mismatch"}
    engine.real_operational = False
    fail_safe_calls = []
    def fail_safe(reason, data=None):
        fail_safe_calls.append((reason, data))
        engine.mode = "PAPER"
        engine.state.mode = "PAPER"
        engine.real_operational = False
        engine.state.status = "SAFE_MODE"
        engine.real_mode_guard.disarm(reason)
    engine._enter_real_fail_safe = fail_safe

    assert not engine._maybe_autonomous_real_promotion()
    assert engine.mode == "PAPER"
    assert engine.state.mode == "PAPER"
    assert not engine.real_operational
    assert engine.state.status == "SAFE_MODE"
    assert fail_safe_calls
    assert fail_safe_calls[0][0] == "autonomous_real_reconciliation_failed"
