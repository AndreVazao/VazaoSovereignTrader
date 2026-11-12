from __future__ import annotations

from types import SimpleNamespace

import pytest
from flask import Flask

from PC_ENGINE.api.office_snapshot import build_office_snapshot, register_office_snapshot


class FakeReadiness:
    def scorecard(self):
        return {"status": "BLOCKED"}


class FakeEngine:
    mode = "PAPER"
    state = SimpleNamespace(status="STOPPED")

    def __init__(self):
        self.config = {"autonomous_execution": {"allow_real": False, "auto_promote_real": False}}

    def snapshot(self):
        return {"status": "STOPPED", "mode": "PAPER", "balance": 123456}


def test_office_snapshot_is_backend_confirmed_and_redacted():
    result = build_office_snapshot(
        FakeEngine(),
        readiness=FakeReadiness(),
        market_data_reader=lambda: {
            "status": "RUNNING", "ok": True, "stale": False, "health_age_ms": 1200,
            "api_key": "must-not-leak",
        },
    )
    assert result["engine"] == {"status": "STOPPED", "mode": "PAPER", "running": False}
    assert result["market_data"]["ok"] is True
    assert result["risk"]["status"] == "BLOCKED"
    assert result["safety"]["paper_only"] is True
    assert result["safety"]["allow_real"] is False
    assert result["verified_tasks"] == []
    assert "balance" not in str(result)
    assert "api_key" not in str(result)
    assert "must-not-leak" not in str(result)


def test_office_snapshot_fails_closed_on_invalid_runtime():
    engine = FakeEngine()
    engine.snapshot = lambda: []
    with pytest.raises(ValueError, match="runtime_snapshot_invalid"):
        build_office_snapshot(
            engine, readiness=FakeReadiness(),
            market_data_reader=lambda: {"status": "UNKNOWN"},
        )


def test_office_snapshot_route_requires_read_scope_and_returns_snapshot():
    app = Flask(__name__)
    engine = FakeEngine()
    denied = {"value": True}

    def require_scope(scope):
        assert scope == "read_private_state"
        if denied["value"]:
            from werkzeug.exceptions import Unauthorized
            raise Unauthorized()

    register_office_snapshot(
        app, engine, require_scope=require_scope,
        readiness=FakeReadiness(),
        market_data_reader=lambda: {"status": "NOT_STARTED", "ok": False, "stale": True},
    )
    client = app.test_client()
    assert client.get("/office/snapshot").status_code == 401
    denied["value"] = False
    response = client.get("/office/snapshot")
    assert response.status_code == 200
    assert response.get_json()["source"] == "vst_backend"


def test_office_snapshot_route_returns_unavailable_without_leaking_exception():
    app = Flask(__name__)
    engine = FakeEngine()
    engine.snapshot = lambda: (_ for _ in ()).throw(RuntimeError("secret/path"))
    register_office_snapshot(
        app, engine, require_scope=lambda scope: None,
        readiness=FakeReadiness(),
        market_data_reader=lambda: {"status": "UNKNOWN"},
    )
    response = app.test_client().get("/office/snapshot")
    assert response.status_code == 503
    assert "secret/path" not in response.get_data(as_text=True)
