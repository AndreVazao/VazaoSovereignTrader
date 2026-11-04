from __future__ import annotations

from typing import Any


BASE_COMPONENTS = ("brain_headless", "chat_cockpit")
MODE_COMPONENTS = {
    "chat": (),
    "pixel": ("office_pixel",),
    "enhanced": ("office_pixel", "office_enhanced"),
    "3d": ("office_pixel", "office_enhanced", "office_3d"),
}
VALID_MODES = frozenset(("auto", *MODE_COMPONENTS))


def plan_components(report: dict[str, Any], requested_mode: str = "auto") -> dict[str, Any]:
    """Create a fail-closed install plan; never install packages or start services."""
    request = str(requested_mode).strip().lower()
    if request not in VALID_MODES:
        raise ValueError(f"Unsupported visual mode: {request}")

    if report.get("schema_version") != 1:
        raise ValueError("Unsupported or missing diagnostics schema_version")
    profile = report.get("visual_profile")
    recommendations = profile.get("recommended_modes") if isinstance(profile, dict) else None
    if not isinstance(recommendations, dict):
        raise ValueError("Diagnostics do not contain visual mode recommendations")

    # Baseline modes are always available; optional modes require explicit positive evidence.
    supported = {
        mode: mode in ("chat", "pixel") or recommendations.get(mode) is True
        for mode in MODE_COMPONENTS
    }
    reasons: list[str] = []
    if request == "auto":
        selected = next((mode for mode in ("3d", "enhanced", "pixel", "chat") if supported[mode]), "chat")
    elif supported[request]:
        selected = request
    else:
        selected = "pixel"
        reasons.append(f"requested_mode_{request}_not_supported_fallback_to_pixel")

    components = list(BASE_COMPONENTS)
    components.extend(MODE_COMPONENTS[selected])
    return {
        "schema_version": 1,
        "requested_mode": request,
        "selected_mode": selected,
        "components_to_install": components,
        "optional_components_to_install": list(MODE_COMPONENTS[selected]),
        "unsupported_modes": [mode for mode in ("enhanced", "3d") if not supported[mode]],
        "reasons": reasons,
        "install_actions_performed": False,
        "network_requests": 0,
        "read_only": True,
        "note": "Plan only. The installer must revalidate capabilities and user selection before installing optional dependencies.",
    }
