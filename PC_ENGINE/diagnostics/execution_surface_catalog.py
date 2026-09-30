from __future__ import annotations

from typing import Any

from PC_ENGINE.execution.surface_health import ExecutionSurface, SurfaceState
from PC_ENGINE.diagnostics.path_utils import resolve_config_path
from PC_ENGINE.execution.surface_feedback_store import ExecutionSurfaceFeedbackStore


def build_execution_surface_catalog(config: dict[str, Any]) -> dict[str, Any]:
    """Build a read-only operational catalog for dashboard signalling.

    This is configuration/transport metadata only. It does not probe venues,
    authorize execution, or infer economic quality.
    """
    browser_cfg = dict(config.get("browser", {}))
    execution_cfg = dict(config.get("execution_surface", {}))
    feedback_path = resolve_config_path(execution_cfg.get("feedback_path", "PC_ENGINE/data/execution/surface_feedback.jsonl"))
    feedback_store = ExecutionSurfaceFeedbackStore(feedback_path, max_records=int(execution_cfg.get("feedback_max_records", 2_000)))
    feedback = feedback_store.snapshot(stale_after_ms=int(execution_cfg.get("feedback_stale_after_ms", 30_000)))
    live_rows = {(str(row["venue_id"]), str(row["surface"])): row for row in feedback["surfaces"]}
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

        base_key = (str(venue_id), surface.value)
        live = live_rows.get(base_key)
        rows.append({
            "venue_id": str(venue_id),
            "surface": surface.value,
            "state": live["state"] if live and enabled else (SurfaceState.DEGRADED.value if enabled else SurfaceState.NOT_CONFIGURED.value),
            "enabled": enabled,
            "source": live["source"] if live and enabled else "configuration",
            "live_probe": bool(live and enabled),
            "connection_state": live["connection_state"] if live and enabled else None,
            "last_feedback_age_ms": live["last_feedback_age_ms"] if live and enabled else None,
            "reconnects": live["reconnects"] if live and enabled else 0,
            "data_write_health": feedback["data_write_health"],
            "detail": live["detail"] if live and enabled else ("Configurada; ainda sem health probe persistente" if enabled else "Não configurada/ativada"),
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

    configured_keys = {(str(row["venue_id"]), str(row["surface"])) for row in rows}
    for key, live in live_rows.items():
        if key in configured_keys:
            continue
        rows.append({
            "venue_id": live["venue_id"], "surface": live["surface"], "state": live["state"],
            "enabled": True, "source": live["source"], "live_probe": True,
            "connection_state": live["connection_state"], "last_feedback_age_ms": live["last_feedback_age_ms"],
            "reconnects": live["reconnects"], "data_write_health": feedback["data_write_health"],
            "detail": live["detail"], "paper_only": True, "orders_submitted": False, "execution_authorized": False,
        })

    return {
        "ok": True,
        "operational_only": True,
        "paper_only": True,
        "orders_submitted": False,
        "execution_authorized": False,
        "venues": rows,
    }
