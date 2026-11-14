from __future__ import annotations

from pathlib import Path

from PC_ENGINE.api.cockpit import COCKPIT_HTML


def test_pc_cockpit_exposes_only_paper_execution_controls() -> None:
    assert "PAPER-only" in COCKPIT_HTML
    assert "AUTORIZAR REAL" not in COCKPIT_HTML
    assert "ATIVAR REAL" not in COCKPIT_HTML
    assert "/real/arm" not in COCKPIT_HTML
    assert "/autonomous-readiness" not in COCKPIT_HTML
    assert "async function setMode(m){if(String(m).toUpperCase()!=='PAPER')" in COCKPIT_HTML


def test_android_client_has_no_real_arming_path() -> None:
    mobile_source = (
        Path(__file__).resolve().parents[1] / "MOBILE_APP" / "main.py"
    ).read_text(encoding="utf-8")
    assert "def arm_real(" not in mobile_source
    assert "/real/arm" not in mobile_source
    assert "só suporta PAPER nesta versão" in mobile_source
