from __future__ import annotations


def summarize_office_snapshot(payload: object) -> dict[str, object]:
    """Validate and reduce the authenticated backend snapshot for the mobile UI."""
    if not isinstance(payload, dict):
        raise ValueError("snapshot_invalid")
    if payload.get("ok") is not True or payload.get("schema_version") != 1:
        raise ValueError("snapshot_unavailable")
    if payload.get("source") != "vst_backend":
        raise ValueError("snapshot_source_invalid")
    engine = payload.get("engine")
    market = payload.get("market_data")
    risk = payload.get("risk")
    safety = payload.get("safety")
    if not all(isinstance(item, dict) for item in (engine, market, risk, safety)):
        raise ValueError("snapshot_sections_invalid")
    tasks = payload.get("verified_tasks", [])
    if not isinstance(tasks, list):
        raise ValueError("snapshot_tasks_invalid")
    return {
        "engine_status": str(engine.get("status", "UNKNOWN")).upper(),
        "mode": str(engine.get("mode", "UNKNOWN")).upper(),
        "running": engine.get("running") is True,
        "market_status": str(market.get("status", "UNKNOWN")).upper(),
        "market_ok": market.get("ok") is True and market.get("stale") is False,
        "risk_status": str(risk.get("status", "UNKNOWN")).upper(),
        "paper_only": safety.get("paper_only") is True,
        "allow_real": safety.get("allow_real") is True,
        "auto_promote_real": safety.get("auto_promote_real") is True,
        "verified_task_count": len(tasks),
        "generated_at": str(payload.get("generated_at", "")),
    }
