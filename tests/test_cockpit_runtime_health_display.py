from __future__ import annotations

from PC_ENGINE.api.cockpit import COCKPIT_HTML


def test_cockpit_surface_panel_exposes_runtime_health_and_freshness() -> None:
    # The UI consumes only the read-only execution-surface catalog response.
    # It must distinguish an absent runtime/unknown age from a healthy probe.
    assert "const runtime=v.runtime_state||'NOT_INSTANTIATED'" in COCKPIT_HTML
    assert "const runtimeHealth=v.runtime_health||'NOT_OBSERVED'" in COCKPIT_HTML
    assert "v.runtime_stale===true?'STALE':v.runtime_stale===false?'FRESH':'UNKNOWN_AGE'" in COCKPIT_HTML
    assert "const runtimeWiring=v.runtime_wiring||'NOT_OBSERVED'" in COCKPIT_HTML
    assert "Runtime '+esc(runtime)+' · saúde '+esc(runtimeHealth)+' · frescura '+esc(runtimeFresh)" in COCKPIT_HTML
