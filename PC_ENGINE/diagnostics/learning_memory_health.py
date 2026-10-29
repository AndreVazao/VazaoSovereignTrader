"""Read-only health classification for the durable learning-memory database."""
from __future__ import annotations

from typing import Any

from PC_ENGINE.learning.memory_backup import verify_learning_memory_backup


def build_learning_memory_health(memory: Any) -> dict[str, object]:
    """Inspect durable-memory storage without writing to it or creating a DB.

    This is a storage diagnostic, not a claim that the learning loop is active
    or that learned evidence is correct. It never changes trading permissions.
    """
    base: dict[str, object] = {
        "component": "durable_learning_memory",
        "paper_only": True,
        "orders_submitted": False,
        "execution_authorized": False,
    }
    if memory is None:
        return {
            **base,
            "status": "NOT_CONFIGURED",
            "reason": "learning_memory_not_configured",
            "learning_records": None,
            "learning_events": None,
        }

    path = getattr(memory, "database_path", None)
    if not isinstance(path, str) or not path.strip():
        return {
            **base,
            "status": "UNKNOWN",
            "reason": "learning_memory_path_unavailable",
            "learning_records": None,
            "learning_events": None,
        }
    if path == ":memory:":
        return {
            **base,
            "status": "UNKNOWN",
            "reason": "in_memory_store_has_no_independent_read_only_probe",
            "learning_records": None,
            "learning_events": None,
        }

    verified = verify_learning_memory_backup(path)
    mapping = {"healthy": "HEALTHY", "degraded": "DEGRADED", "missing": "MISSING"}
    return {
        **base,
        "status": mapping.get(str(verified.get("status")), "UNKNOWN"),
        "reason": verified.get("reason"),
        "integrity": verified.get("integrity"),
        "learning_records": verified.get("learning_records"),
        "learning_events": verified.get("learning_events"),
    }
