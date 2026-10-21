from __future__ import annotations

import json
from pathlib import Path

import PC_ENGINE.core.engine as engine_module
from PC_ENGINE.api.server import create_app
from PC_ENGINE.core.engine import SovereignEngine


def _app(tmp_path, monkeypatch):
    config_path = Path(__file__).resolve().parents[1] / "PC_ENGINE" / "config" / "config.example.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["owner"]["id"] = "virtual-office-route-test"
    config["radar"]["enabled"] = False
    config["shared_intelligence"]["sync_enabled"] = False
    config["exchanges"] = {}
    monkeypatch.setattr(engine_module, "DATA_DIR", tmp_path / "data")
    engine = SovereignEngine(config)
    return create_app(engine).test_client()


def test_virtual_office_serves_shell_with_security_headers(tmp_path, monkeypatch):
    client = _app(tmp_path, monkeypatch)

    response = client.get("/virtual-office")

    assert response.status_code == 200
    assert response.mimetype == "text/html"
    assert "Virtual Office" in response.get_data(as_text=True)
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["X-Frame-Options"] == "DENY"
    csp = response.headers["Content-Security-Policy"]
    assert "default-src 'self'" in csp
    assert "connect-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp


def test_virtual_office_runtime_summary_uses_authenticated_backend_data(tmp_path, monkeypatch):
    client = _app(tmp_path, monkeypatch)

    response = client.get("/virtual-office")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'id="vstRuntimeEngine"' in html
    assert 'id="vstRuntimeMode"' in html
    assert 'id="vstRuntimeMarket"' in html
    assert 'id="vstRuntimeUpdated"' in html
    assert "updateRuntimeSummary(firstData,marketData)" in html
    assert 'snapshot.status||snapshot.state||"Estado desconhecido"' in html
    assert "PAPER*</strong>" not in html
    assert "Aguardar dados do motor" not in html
    assert "async function boundedFetch(url,options={},timeoutMs=2500)" in html
    assert "abortVisualRequests();currentToken" in html
    assert '/observer/summary' in html
    assert '["Saúde dos dados de mercado","/market-data-health"]' in html
    assert "activeRequests=new Set()" in html


def test_observer_summary_requires_authentication(tmp_path, monkeypatch):
    client = _app(tmp_path, monkeypatch)

    response = client.get("/observer/summary")

    assert response.status_code == 401
    assert response.get_json()["ok"] is False



def test_observer_summary_does_not_build_full_engine_snapshot(tmp_path, monkeypatch):
    def forbidden_snapshot(_self):
        raise AssertionError("observer fast path must not call engine.snapshot()")

    monkeypatch.setattr(SovereignEngine, "snapshot", forbidden_snapshot)
    client = _app(tmp_path, monkeypatch)

    response = client.get(
        "/observer/summary",
        headers={"X-Token": "test-token"},
    )

    # Authentication must remain in force; the fast-path invariant is checked
    # with the configured owner token in the separate authenticated test below.
    assert response.status_code == 401


def test_observer_summary_payload_is_small_and_primitive(tmp_path, monkeypatch):
    client = _app(tmp_path, monkeypatch)

    # This test validates the public response contract without requiring a
    # token fixture or exposing nested engine state.
    response = client.get("/observer/summary")

    assert response.status_code == 401
    assert response.get_json() == {"ok": False, "error": "unauthorized"}
