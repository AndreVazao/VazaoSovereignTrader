from __future__ import annotations

from pathlib import Path


SHELL = Path("virtual_office/prototype/full_cockpit_shell.html").read_text(encoding="utf-8")


def test_virtual_office_mobile_layout_respects_system_safe_areas() -> None:
    # Keep the header and scrollable work area clear of Android/iOS status and gesture areas.
    assert 'name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"' in SHELL
    assert "body{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}" in SHELL
    assert ".app{height:calc(100dvh - env(safe-area-inset-top,0px) - env(safe-area-inset-bottom,0px));min-height:0;grid-template-rows:58px 1fr}" in SHELL
    assert ".main{height:calc(100dvh - 58px - env(safe-area-inset-top,0px) - env(safe-area-inset-bottom,0px));padding:12px}" in SHELL


def test_virtual_office_respects_reduced_motion_preferences() -> None:
    # Animated office characters are decorative and must not force motion on users
    # whose operating system requests reduced motion.
    assert "@media(prefers-reduced-motion:reduce)" in SHELL
    assert ".idle-person,.idle-person *,.idle-bubble{animation:none!important}" in SHELL


def test_virtual_office_runtime_poll_is_authenticated_bounded_and_read_only() -> None:
    # The observer may read status, but must not invent work or issue trading mutations.
    assert "async function pollRuntimeStatus()" in SHELL
    assert "if(!currentToken||busy||document.hidden)return;" in SHELL
    assert 'headers={"X-Token":currentToken,"Accept":"application/json"}' in SHELL
    assert 'method:"GET"' in SHELL
    assert 'cache:"no-store",credentials:"omit"' in SHELL
    assert 'setInterval(pollRuntimeStatus,10000)' in SHELL
    assert "/learning-memory/runtime" in SHELL
    assert "/learning-memory/health" in SHELL
    assert "/market-data-health" in SHELL
    assert "boundedFetch" in SHELL
    assert "currentToken=\"\"" in SHELL
