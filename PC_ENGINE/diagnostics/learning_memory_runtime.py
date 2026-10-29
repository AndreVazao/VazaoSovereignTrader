"""Read-only runtime diagnostics for the learning-memory consumer."""
from __future__ import annotations

from typing import Any


def build_learning_memory_runtime_diagnostics(engine: Any) -> dict[str, object]:
    """Report memory wiring and producer-loop liveness without implying learning quality."""
    base: dict[str, object] = {
        "component": "learning_memory_runtime",
        "paper_only": True,
        "orders_submitted": False,
        "execution_authorized": False,
    }
    if engine is None:
        return {**base, "status": "UNKNOWN", "reason": "engine_unavailable"}

    closed = getattr(engine, "_closed", None)
    main_thread = getattr(engine, "thread", None)
    main_alive = main_thread.is_alive() if callable(getattr(main_thread, "is_alive", None)) else None
    operational = getattr(getattr(engine, "state", None), "operational", {}) or {}
    memory_state = operational.get("learning_memory", {})
    memory_state = memory_state if isinstance(memory_state, dict) else {}
    memory = getattr(engine, "learning_memory", None)
    autonomous = getattr(engine, "autonomous_research", None)
    snapshot_fn = getattr(autonomous, "snapshot", None)
    worker_snapshot = snapshot_fn() if callable(snapshot_fn) else {}
    durable = worker_snapshot.get("durable_memory", {}) if isinstance(worker_snapshot, dict) else {}
    durable = durable if isinstance(durable, dict) else {}
    wired = autonomous is not None and getattr(autonomous, "learning_memory", None) is memory and memory is not None
    enabled = memory_state.get("enabled", memory is not None)
    research_cfg = getattr(engine, "config", {}).get("research", {})
    observation_enabled = bool(research_cfg.get("enabled", True)) and bool(
        research_cfg.get("autonomous_observation_enabled", True)
    )

    if closed is True:
        status, reason = "CLOSED", "engine_terminally_closed"
    elif not observation_enabled:
        status, reason = "DISABLED", "autonomous_observation_disabled"
    elif enabled is False or memory is None:
        status, reason = "DEGRADED", "durable_memory_not_available"
    elif not wired:
        status, reason = "DEGRADED", "autonomous_research_memory_not_wired"
    elif main_alive is False:
        status, reason = "STOPPED", "engine_loop_not_running"
    elif main_alive is None:
        status, reason = "UNKNOWN", "engine_thread_state_unavailable"
    elif int(durable.get("write_failures", 0) or 0) > 0:
        status, reason = "DEGRADED", "durable_memory_write_failures"
    else:
        status, reason = "RUNNING", "memory_consumer_wired_engine_loop_alive"

    return {
        **base,
        "status": status,
        "reason": reason,
        "engine_loop": "RUNNING" if main_alive is True else "STOPPED" if main_alive is False else "UNKNOWN",
        "memory_consumer_wired": bool(wired),
        "memory_storage_state": str(memory_state.get("state", "UNKNOWN")),
        "write_failures": int(durable.get("write_failures", 0) or 0),
        "last_error": str(durable.get("last_error", "")) or None,
        "learning_quality_verified": False,
    }
