from __future__ import annotations

from pathlib import Path


SHELL = Path("virtual_office/prototype/full_cockpit_shell.html").read_text(encoding="utf-8")


def test_virtual_office_polls_single_authenticated_read_only_snapshot():
    assert 'window.location.origin+"/office/snapshot"' in SHELL
    assert 'headers:{"X-Token":currentToken,"Accept":"application/json"}' in SHELL
    assert 'method:"GET"' in SHELL
    assert 'credentials:"omit"' in SHELL
    assert 'cache:"no-store"' in SHELL
    assert "window.setInterval(pollRuntimeStatus,10000)" in SHELL
    assert 'snapshot.schema_version!==1' in SHELL
    assert 'snapshot.source!=="vst_backend"' in SHELL
    assert "/learning-memory/runtime" not in SHELL
    assert "/learning-memory/health" not in SHELL
    assert "/market-data-health" not in SHELL


def test_virtual_office_never_infers_agent_activity_from_engine_liveness():
    assert 'window.vstSetAmbientBackendState(true,false,false)' in SHELL
    assert 'window.vstUpdateAgentTaskState' in SHELL
    assert "p.backendConfirmed!==true" in SHELL
    assert "firstData.working===true" not in SHELL
    assert "firstData.active_work===true" not in SHELL


def test_virtual_office_keeps_token_in_page_memory_and_clears_polling_on_disconnect():
    assert 'let currentToken=""' in SHELL
    assert 'localStorage.setItem("vstApiToken"' not in SHELL
    assert "window.clearInterval(pollTimer)" in SHELL
    assert 'state("Estado indisponível"' in SHELL
