from __future__ import annotations

from pathlib import Path


SHELL = Path("virtual_office/prototype/full_cockpit_shell.html").read_text(encoding="utf-8")


def test_virtual_office_polls_real_read_only_runtime_endpoints():
    assert 'base+"/learning-memory/runtime"' in SHELL
    assert 'base+"/learning-memory/health"' in SHELL
    assert 'base+"/market-data-health"' in SHELL
    assert "window.setInterval(pollRuntimeStatus,10000)" in SHELL
    assert 'headers={"X-Token":currentToken' in SHELL
    assert 'credentials:"omit"' in SHELL
    assert 'cache:"no-store"' in SHELL


def test_virtual_office_never_infers_agent_activity_from_engine_liveness():
    assert 'window.vstSetAmbientBackendState(true,false,false)' in SHELL
    assert 'window.vstUpdateAgentTaskState' in SHELL
    assert "p.backendConfirmed!==true" in SHELL
    assert "firstData.working===true" not in SHELL
    assert "firstData.active_work===true" not in SHELL


def test_virtual_office_keeps_token_in_page_memory_and_clears_polling_on_disconnect():
    assert "let currentToken=\"\"" in SHELL
    assert "localStorage.setItem(\"vstApiToken\"" not in SHELL
    assert "window.clearInterval(pollTimer)" in SHELL
    assert 'state("Estado indisponível"' in SHELL
