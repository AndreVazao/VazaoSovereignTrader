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
    assert "activeRequests=new Set()" in html
