"""Read-only runtime diagnostics for the learning-memory consumer."""
from __future__ import annotations

from typing import Any


def _thread_state(thread: Any) -> str:
    """Return RUNNING/STOPPED/UNKNOWN without assuming an absent thread is healthy."""
    is_alive = getattr(thread, "is_alive", None)
    if not callable(is_alive):
        return "UNKNOWN"
    try:
        return "RUNNING" if is_alive() else "STOPPED"
    except Exception:
        return "UNKNOWN"


def build_learning_memory_runtime_diagnostics(engine: Any) -> dict[str, object]:
    """Report memory wiring and both runtime worker states without implying quality."""
    base: dict[str, object] = {
        "component": "learning_memory_runtime",
        "paper_only": True,
        "orders_submitted": False,
        "execution_authorized": False,
    }
    if engine is None:
        return {
            **base,
            "status": "UNKNOWN",
            "reason": "engine_unavailable",
            "engine_loop": "UNKNOWN",
            "research_worker": "UNKNOWN",
        }

    closed = getattr(engine, "_closed", None)
    engine_loop = _thread_state(getattr(engine, "thread", None))
    research_worker = _thread_state(getattr(engine, "research_thread", None))
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
    research_worker_expected = bool(research_cfg.get("enabled", True))
    write_failures = int(durable.get("write_failures", 0) or 0)

    if closed is True:
        status, reason = "CLOSED", "engine_terminally_closed"
    elif not observation_enabled:
        status, reason = "DISABLED", "autonomous_observation_disabled"
    elif enabled is False or memory is None:
        status, reason = "DEGRADED", "durable_memory_not_available"
    elif not wired:
        status, reason = "DEGRADED", "autonomous_research_memory_not_wired"
    elif engine_loop == "STOPPED":
        status, reason = "STOPPED", "engine_loop_not_running"
    elif engine_loop == "UNKNOWN":
        status, reason = "UNKNOWN", "engine_thread_state_unavailable"
    elif research_worker_expected and research_worker == "STOPPED":
        status, reason = "DEGRADED", "research_worker_not_running"
    elif research_worker_expected and research_worker == "UNKNOWN":
        status, reason = "UNKNOWN", "research_worker_state_unavailable"
    elif write_failures > 0:
        status, reason = "DEGRADED", "durable_memory_write_failures"
    else:
        status, reason = "RUNNING", "engine_loop_and_research_worker_observed"

    return {
        **base,
        "status": status,
        "reason": reason,
        "engine_loop": engine_loop,
        "research_worker": research_worker,
        "research_worker_expected": research_worker_expected,
        "memory_consumer_wired": bool(wired),
        "memory_storage_state": str(memory_state.get("state", "UNKNOWN")),
        "write_failures": write_failures,
        "last_error": str(durable.get("last_error", "")) or None,
        "learning_quality_verified": False,
    }
