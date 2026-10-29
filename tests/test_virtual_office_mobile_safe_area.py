from __future__ import annotations

from pathlib import Path


SHELL = Path("virtual_office/prototype/full_cockpit_shell.html").read_text(encoding="utf-8")


def test_virtual_office_mobile_layout_respects_system_safe_areas() -> None:
    # Keep the header and scrollable work area clear of Android/iOS status and gesture areas.
    assert "body{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}" in SHELL
    assert ".app{height:calc(100dvh - env(safe-area-inset-top,0px) - env(safe-area-inset-bottom,0px));min-height:0;grid-template-rows:58px 1fr}" in SHELL
    assert ".main{height:calc(100dvh - 58px - env(safe-area-inset-top,0px) - env(safe-area-inset-bottom,0px));padding:12px}" in SHELL
