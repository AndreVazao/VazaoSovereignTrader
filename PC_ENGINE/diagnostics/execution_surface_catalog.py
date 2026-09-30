from __future__ import annotations

from typing import Any

from PC_ENGINE.execution.surface_health import ExecutionSurface, SurfaceState


def build_execution_surface_catalog(config: dict[str, Any]) -> dict[str, Any]:
    """Build a read-only operational catalog for dashboard signalling.

    This is configuration/transport metadata only. It does not probe venues,
    authorize execution, or infer economic quality.
    """
    browser_cfg = dict(config.get("browser", {}))
    browser_enabled = bool(browser_cfg.get("enabled", False))
    platforms = browser_cfg.get("platforms") or {}

    rows: list[dict[str, Any]] = []
    for venue_id, venue_cfg_raw in platforms.items():
        venue_cfg = dict(venue_cfg_raw or {})
        enabled = bool(venue_cfg.get("enabled", browser_enabled))
        surface_raw = str(venue_cfg.get("surface", "WEB_BROWSER")).upper()
        try:
            surface = ExecutionSurface(surface_raw)
        except ValueError:
            surface = ExecutionSurface.WEB_BROWSER

        rows.append({
            "venue_id": str(venue_id),
            "surface": surface.value,
            "state": SurfaceState.DEGRADED.value if enabled else SurfaceState.NOT_CONFIGURED.value,
            "enabled": enabled,
            "source": "configuration",
            "live_probe": False,
            "detail": (
                "Configurada; ainda sem health probe persistente"
                if enabled
                else "Não configurada/ativada"
            ),
            "paper_only": True,
            "orders_submitted": False,
            "execution_authorized": False,
        })

    if not rows:
        rows.append({
            "venue_id": "browser",
            "surface": ExecutionSurface.WEB_BROWSER.value,
            "state": SurfaceState.DEGRADED.value if browser_enabled else SurfaceState.NOT_CONFIGURED.value,
            "enabled": browser_enabled,
            "source": "configuration",
            "live_probe": False,
            "detail": (
                "Browser global ativo; venues ainda sem configuração específica"
                if browser_enabled
                else "Browser execution não configurado"
            ),
            "paper_only": True,
            "orders_submitted": False,
            "execution_authorized": False,
        })

    return {
        "ok": True,
        "operational_only": True,
        "paper_only": True,
        "orders_submitted": False,
        "execution_authorized": False,
        "venues": rows,
    }
