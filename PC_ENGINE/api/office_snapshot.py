from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

from flask import Flask, jsonify


def build_office_snapshot(
    engine: Any,
    *,
    readiness: Any,
    market_data_reader: Callable[[], dict[str, Any]],
) -> dict[str, Any]:
    """Build a minimal, truthful, read-only snapshot for every VST interface.

    Only backend-confirmed runtime facts are exposed. No balances, credentials,
    filesystem paths, order details, or synthetic agent/task activity are returned.
    """
    runtime = engine.snapshot()
    if not isinstance(runtime, dict):
        raise ValueError("runtime_snapshot_invalid")

    mode = str(runtime.get("mode", getattr(engine, "mode", "UNKNOWN"))).upper()
    status = str(runtime.get("status", getattr(getattr(engine, "state", None), "status", "UNKNOWN"))).upper()
    market = market_data_reader()
    if not isinstance(market, dict):
        market = {"status": "INVALID", "ok": False, "stale": True}

    auto_cfg = getattr(engine, "config", {}).get("autonomous_execution", {})
    if not isinstance(auto_cfg, dict):
        auto_cfg = {}

    risk_status = "UNKNOWN"
    try:
        scorecard = readiness.scorecard()
        if isinstance(scorecard, dict):
            risk_status = str(scorecard.get("status", scorecard.get("overall_status", "UNKNOWN"))).upper()
    except Exception:
        risk_status = "UNAVAILABLE"

    return {
        "ok": True,
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "vst_backend",
        "engine": {"status": status, "mode": mode, "running": status == "RUNNING"},
        "market_data": {
            "status": str(market.get("status", "UNKNOWN")).upper(),
            "ok": market.get("ok") is True,
            "stale": market.get("stale") is not False,
            "health_age_ms": market.get("health_age_ms"),
        },
        "risk": {"status": risk_status},
        "safety": {
            "allow_real": bool(auto_cfg.get("allow_real", False)),
            "auto_promote_real": bool(auto_cfg.get("auto_promote_real", False)),
            "paper_only": mode == "PAPER",
            "orders_submitted_by_snapshot": False,
        },
        # Deliberately empty until the backend exposes a verified task registry.
        "verified_tasks": [],
        "activity_source": "no_verified_task_registry",
    }


def register_office_snapshot(
    app: Flask,
    engine: Any,
    *,
    require_scope: Callable[[str], Any],
    readiness: Any,
    market_data_reader: Callable[[], dict[str, Any]],
) -> None:
    @app.get("/office/snapshot")
    def office_snapshot():
        require_scope("read_private_state")
        try:
            return jsonify(build_office_snapshot(
                engine,
                readiness=readiness,
                market_data_reader=market_data_reader,
            ))
        except (OSError, ValueError, TypeError, RuntimeError):
            return jsonify({"ok": False, "error": "office_snapshot_unavailable"}), 503
