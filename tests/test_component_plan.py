from __future__ import annotations

import pytest

from PC_ENGINE.tools.component_plan import plan_components


def diagnostics(*, enhanced: bool = False, three_d: bool = False) -> dict:
    return {
        "schema_version": 1,
        "visual_profile": {
            "recommended_modes": {
                "chat": True,
                "pixel": True,
                "enhanced": enhanced,
                "3d": three_d,
            }
        },
    }


def test_chat_plan_never_selects_optional_graphics():
    plan = plan_components(diagnostics(enhanced=True, three_d=True), "chat")
    assert plan["selected_mode"] == "chat"
    assert plan["components_to_install"] == ["brain_headless", "chat_cockpit"]
    assert plan["optional_components_to_install"] == []
    assert plan["install_actions_performed"] is False
    assert plan["network_requests"] == 0


def test_auto_fails_closed_to_pixel_when_renderer_capability_is_unknown():
    plan = plan_components(diagnostics(), "auto")
    assert plan["selected_mode"] == "pixel"
    assert plan["components_to_install"] == ["brain_headless", "chat_cockpit", "office_pixel"]
    assert "office_enhanced" not in plan["components_to_install"]
    assert "office_3d" not in plan["components_to_install"]


def test_explicit_unsupported_3d_falls_back_to_pixel():
    plan = plan_components(diagnostics(enhanced=True, three_d=False), "3d")
    assert plan["selected_mode"] == "pixel"
    assert plan["reasons"] == ["requested_mode_3d_not_supported_fallback_to_pixel"]


def test_auto_selects_highest_positive_recommendation():
    plan = plan_components(diagnostics(enhanced=True, three_d=True), "auto")
    assert plan["selected_mode"] == "3d"
    assert plan["components_to_install"] == [
        "brain_headless", "chat_cockpit", "office_pixel", "office_enhanced", "office_3d"
    ]


def test_planner_rejects_unknown_schema_or_missing_recommendations():
    with pytest.raises(ValueError, match="schema_version"):
        plan_components({"schema_version": 2}, "auto")
    with pytest.raises(ValueError, match="recommendations"):
        plan_components({"schema_version": 1}, "auto")


def test_planner_rejects_unknown_mode():
    with pytest.raises(ValueError, match="Unsupported visual mode"):
        plan_components(diagnostics(), "ultra")
