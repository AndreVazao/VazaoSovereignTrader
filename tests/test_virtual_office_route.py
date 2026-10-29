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
    app = create_app(engine)
    app.config["TEST_ENGINE"] = engine
    return app.test_client()


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
    assert '/learning-memory/runtime' in html
    assert '/learning-memory/health' in html
    assert 'window.setInterval(pollRuntimeStatus,10000)' in html
    assert '["Saúde dos dados de mercado","/market-data-health"]' in html
    assert "activeRequests=new Set()" in html
    assert 'id="vstConnectionBadge"' in html
    assert "DEMONSTRAÇÃO · NÃO LIGADO" in html
    assert "PROTÓTIPO · SEM LIGAÇÃO AO MOTOR" not in html
    assert "vst-department-change" in html
    assert 'body:JSON.stringify({message,department:selectedDepartment})' in html
    assert "conversationHistory=Object.create(null)" in html


def test_observer_summary_requires_authentication(tmp_path, monkeypatch):
    client = _app(tmp_path, monkeypatch)

    response = client.get("/observer/summary")

    assert response.status_code == 401
    assert response.get_json()["ok"] is False




def test_observer_summary_does_not_build_full_engine_snapshot(tmp_path, monkeypatch):
    monkeypatch.setenv("VST_LOCAL_TOKEN", "observer-test-secret")

    def forbidden_snapshot(_self):
        raise AssertionError("observer fast path must not call engine.snapshot()")

    monkeypatch.setattr(SovereignEngine, "snapshot", forbidden_snapshot)
    client = _app(tmp_path, monkeypatch)

    response = client.get(
        "/observer/summary",
        headers={"X-Token": "observer-test-secret"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert set(payload) == {
        "ok",
        "status",
        "mode",
        "open_positions_count",
        "opportunities_count",
        "updated_at_ms",
    }
    assert isinstance(payload["status"], str)
    assert isinstance(payload["mode"], str)
    assert isinstance(payload["open_positions_count"], int)
    assert isinstance(payload["opportunities_count"], int)
    assert isinstance(payload["updated_at_ms"], int)


def test_observer_summary_rejects_missing_token_without_snapshot(tmp_path, monkeypatch):
    def forbidden_snapshot(_self):
        raise AssertionError("observer fast path must not call engine.snapshot()")

    monkeypatch.delenv("VST_LOCAL_TOKEN", raising=False)
    monkeypatch.setattr(SovereignEngine, "snapshot", forbidden_snapshot)
    client = _app(tmp_path, monkeypatch)

    response = client.get("/observer/summary")

    assert response.status_code == 401
    assert response.get_json() == {"ok": False, "error": "unauthorized"}



def test_observer_summary_does_not_acquire_engine_lock(tmp_path, monkeypatch):
    monkeypatch.setenv("VST_LOCAL_TOKEN", "observer-test-secret")
    client = _app(tmp_path, monkeypatch)
    engine = client.application.config["TEST_ENGINE"]

    class ForbiddenLock:
        def __enter__(self):
            raise AssertionError("observer HTTP request must not acquire engine.lock")

        def __exit__(self, *_args):
            return False

    engine.lock = ForbiddenLock()
    response = client.get(
        "/observer/summary",
        headers={"X-Token": "observer-test-secret"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert set(payload) == {
        "ok",
        "status",
        "mode",
        "open_positions_count",
        "opportunities_count",
        "updated_at_ms",
    }


def test_observer_timing_requires_authentication(tmp_path, monkeypatch):
    monkeypatch.setenv("VST_LOCAL_TOKEN", "timing-test-secret")
    client = _app(tmp_path, monkeypatch)

    response = client.get("/observer/timing")

    assert response.status_code == 401
    assert response.get_json() == {"ok": False, "error": "unauthorized"}


def test_observer_timing_returns_bounded_authenticated_metrics(tmp_path, monkeypatch):
    monkeypatch.setenv("VST_LOCAL_TOKEN", "timing-test-secret")
    client = _app(tmp_path, monkeypatch)
    engine = client.application.config["TEST_ENGINE"]
    engine.runtime_timing_metrics.record_ns("runtime_cycle", 1_000_000)
    engine.runtime_timing_metrics.record_ns("runtime_cycle", 2_000_000)
    engine.runtime_timing_metrics.record_ns("observer_lock_wait", 100)
    engine.runtime_timing_metrics.record_ns("observer_lock_hold", 200)

    response = client.get(
        "/observer/timing",
        headers={"X-Token": "timing-test-secret"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert set(payload["metrics"]) == {
        "runtime_cycle",
        "observer_lock_wait",
        "observer_lock_hold",
    }
    cycle = payload["metrics"]["runtime_cycle"]
    assert cycle["count"] == 2
    assert cycle["sample_count"] == 2
    assert cycle["p50_ns"] == 1_000_000
    assert cycle["p99_ns"] == 2_000_000
    # Engine initialization publishes an initial observer snapshot, so real
    # lock timings may already exist before the synthetic samples are recorded.
    assert payload["metrics"]["observer_lock_wait"]["count"] >= 1
    assert payload["metrics"]["observer_lock_wait"]["max_ns"] >= 100
    assert payload["metrics"]["observer_lock_hold"]["count"] >= 1
    assert payload["metrics"]["observer_lock_hold"]["max_ns"] >= 200
    assert payload["metrics"]["observer_lock_wait"]["sample_count"] <= 512
    assert payload["metrics"]["observer_lock_hold"]["sample_count"] <= 512


def test_assistant_message_rejects_unknown_department(tmp_path, monkeypatch):
    monkeypatch.setenv("VST_LOCAL_TOKEN", "office-department-test-token")
    client = _app(tmp_path, monkeypatch)

    response = client.post(
        "/assistant/message",
        headers={"X-Token": "office-department-test-token"},
        json={"message": "Olá", "department": "unknown-agent"},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "assistant_department_invalid"


def test_assistant_message_returns_selected_department_context(tmp_path, monkeypatch):
    monkeypatch.setenv("VST_LOCAL_TOKEN", "office-department-test-token")
    client = _app(tmp_path, monkeypatch)

    response = client.post(
        "/assistant/message",
        headers={"X-Token": "office-department-test-token"},
        json={"message": "Olá", "department": "radar"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["department"] == "radar"
    assert payload["department_label"] == "Market Radar"
    assert payload["intent"] == "DEPARTMENT_STATUS"
    assert payload["data"]["status"] == "NOT_STARTED"
    assert payload["data"]["stale"] is True
    assert payload["execution_authorized"] is False


def test_assistant_message_uses_department_read_handler(tmp_path, monkeypatch):
    monkeypatch.setenv("VST_LOCAL_TOKEN", "office-department-reader-token")
    client = _app(tmp_path, monkeypatch)

    response = client.post(
        "/assistant/message",
        headers={"X-Token": "office-department-reader-token"},
        json={"message": "Qual é o estado?", "department": "markets"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["intent"] == "DEPARTMENT_STATUS"
    assert payload["department"] == "markets"
    assert isinstance(payload["data"]["venues"], list)
    assert "Saúde operacional" in payload["reply"]
    assert payload["execution_authorized"] is False

 
def test_virtual_office_keeps_required_departments_separate_and_safe(tmp_path, monkeypatch):
    client = _app(tmp_path, monkeypatch)
    html = client.get("/virtual-office").get_data(as_text=True)

    for department in ("comparison", "analysis", "memory", "fast"):
        assert f'data-room="{department}"' in html
        assert f'{department}:[' in html
        assert f'{department}:"' in html

    assert "Comparação entre Exchanges" in html
    assert "Resposta Rápida" in html
    assert "subordinada a todos os gates de risco" in html
    assert "Nenhum estado de agente ou atividade está ligado nesta demonstração." in html

 
def test_virtual_office_shows_offline_ambient_life_and_health_room(tmp_path, monkeypatch):
    client = _app(tmp_path, monkeypatch)
    html = client.get("/virtual-office").get_data(as_text=True)

    assert 'id="idleScene"' in html
    assert "SEM LIGAÇÃO · SIMULAÇÃO LOCAL" in html
    assert "Pausa na cafetaria" in html
    assert "Pausa curta no ginásio" in html
    assert 'data-room="health"' in html
    assert 'health:["Saúde & Enfermaria"' in html
    assert "não executa verificações reais" in html
    assert "window.vstSetAmbientBackendState(true,false,false)" in html
    assert "O motor reporta atividade; animações de trabalho ainda não estão ligadas." in html


def test_virtual_office_only_shows_progress_for_backend_confirmed_tasks_and_has_focus_controls(tmp_path, monkeypatch):
    client = _app(tmp_path, monkeypatch)
    html = client.get("/virtual-office").get_data(as_text=True)

    assert 'data-vst-zoom="in"' in html
    assert 'data-vst-zoom="out"' in html
    assert 'data-vst-zoom="reset"' in html
    assert 'data-vst-focus="toggle"' in html
    assert 'id="vstTalkToChief"' in html
    assert "window.vstUpdateAgentTaskState=function(payload)" in html
    assert "p.backendConfirmed!==true" in html
    assert 'const progress=status==="completed"?100:Math.floor(numeric)' in html
    assert "não gráfico de mercado" in html
    assert "A barra só aparece com um evento de tarefa validado." in html


def test_virtual_office_has_manual_render_profiles_and_persists_selection(tmp_path, monkeypatch):
    client = _app(tmp_path, monkeypatch)
    html = client.get("/virtual-office").get_data(as_text=True)

    assert 'id="vstRenderProfile"' in html
    for profile in ("auto", "standard", "pixel", "stick", "clear", "cinematic", "compact"):
        assert f'<option value="{profile}">' in html
    assert "localStorage.setItem(key,profile)" in html
    assert "window.vstSetRenderProfile=function(profile)" in html
    assert "Seleção manual: " in html
    assert "não é 3D/WebGL real" in html
    assert "A escolha manual fica selecionada" not in html
