"""Regression gate for PAPER startup health and durable learning across restarts.

This is a deterministic component-level lifecycle test, not proof that the
packaged Windows process or installer preserves a real user's vault.
"""
from __future__ import annotations

import json
from pathlib import Path

from PC_ENGINE.core.recovery import RecoveryManager
from PC_ENGINE.core.startup_health import StartupHealth
from PC_ENGINE.learning.sqlite_memory import SQLiteLearningMemory


def _startup_report(runtime_dir: Path) -> dict:
    recovery = RecoveryManager(runtime_dir / "runtime_state.json")
    return StartupHealth(runtime_dir / "startup").run(recovery)


def test_paper_lifecycle_preserves_synthetic_learning_without_duplicate_write(
    tmp_path: Path,
) -> None:
    """A clean close/reopen must retain one synthetic record and its event journal."""
    vault = tmp_path / "vault"
    runtime = tmp_path / "runtime"
    learning_db = vault / "learning" / "learning.sqlite3"
    vault.mkdir()
    runtime.mkdir()

    first_health = _startup_report(runtime)
    assert first_health["status"] == "READY"
    assert first_health["paper_only"] is True
    assert first_health["real_promotion_attempted"] is False
    assert first_health["checks"]["startup_mode"]["effective"] == "PAPER"
    assert first_health["checks"]["recovery_integrity"]["ok"] is True

    with SQLiteLearningMemory(learning_db) as memory:
        saved = memory.put(
            key="synthetic.lifecycle.restart-check",
            value={"kind": "synthetic", "sample_count": 1, "real_execution": False},
            department="validation",
            provenance="local-lifecycle-test",
            status="testing",
            confidence=0.0,
        )
        assert saved.version == 1
        assert len(memory.list_events(key=saved.key)) == 1

    # A new memory connection and startup-health instance model a process restart.
    second_health = _startup_report(runtime)
    assert second_health["status"] == "READY"
    assert second_health["paper_only"] is True
    assert second_health["real_promotion_attempted"] is False
    assert second_health["checks"]["recovery_integrity"]["ok"] is True

    with SQLiteLearningMemory(learning_db) as reopened:
        restored = reopened.get("synthetic.lifecycle.restart-check")
        assert restored is not None
        assert restored == saved
        events = reopened.list_events(key=saved.key)
        assert len(events) == 1
        assert events[0].version == 1
        assert events[0].event_type == "put"

    persisted_report = json.loads(
        (runtime / "startup" / "startup_health.json").read_text(encoding="utf-8")
    )
    assert persisted_report["status"] == "READY"
    assert persisted_report["paper_only"] is True
    assert persisted_report["real_promotion_attempted"] is False
    assert learning_db.is_file()
    assert learning_db.parent == vault / "learning"
