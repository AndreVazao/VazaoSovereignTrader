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


def _startup_report(runtime_dir: Path, recovery: RecoveryManager) -> dict:
    return StartupHealth(runtime_dir / "startup", {"mode": "PAPER"}).run(recovery)


def test_paper_lifecycle_preserves_synthetic_learning_without_duplicate_write(
    tmp_path: Path,
) -> None:
    """First boot fails closed; a clean baseline and cold restart preserve learning."""
    vault = tmp_path / "vault"
    runtime = tmp_path / "runtime"
    learning_db = vault / "learning" / "learning.sqlite3"
    vault.mkdir()
    runtime.mkdir()

    state_path = runtime / "runtime_state.json"
    first_process_recovery = RecoveryManager(state_path)

    # No primary or backup snapshot exists on a true first launch.
    first_boot = _startup_report(runtime, first_process_recovery)
    assert first_boot["status"] == "SAFE_STATE"
    assert first_boot["paper_only"] is True
    assert first_boot["real_promotion_attempted"] is False
    assert first_boot["checks"]["startup_mode"]["effective"] == "PAPER"
    assert first_boot["checks"]["recovery_integrity"]["ok"] is False
    assert first_boot["critical_checks"] == ["recovery_integrity"]

    # An explicit empty PAPER-safe baseline is required before READY.
    first_process_recovery.save_positions({}, runtime_status="OFF")
    ready_health = _startup_report(runtime, first_process_recovery)
    assert ready_health["status"] == "READY"
    assert ready_health["paper_only"] is True
    assert ready_health["real_promotion_attempted"] is False
    assert ready_health["checks"]["recovery_integrity"]["ok"] is True

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

    # Recreate the recovery manager as a separate process would after restart.
    restarted_process_recovery = RecoveryManager(state_path)
    second_health = _startup_report(runtime, restarted_process_recovery)
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
