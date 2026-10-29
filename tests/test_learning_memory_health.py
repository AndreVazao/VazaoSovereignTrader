from __future__ import annotations

from pathlib import Path

from PC_ENGINE.diagnostics.learning_memory_health import build_learning_memory_health
from PC_ENGINE.learning.sqlite_memory import SQLiteLearningMemory


class MemoryPath:
    def __init__(self, path: str):
        self.database_path = path


def test_learning_memory_health_reports_not_configured_and_unknown_states():
    not_configured = build_learning_memory_health(None)
    assert not_configured["status"] == "NOT_CONFIGURED"
    assert not_configured["execution_authorized"] is False

    unknown = build_learning_memory_health(MemoryPath(":memory:"))
    assert unknown["status"] == "UNKNOWN"
    assert unknown["reason"] == "in_memory_store_has_no_independent_read_only_probe"


def test_learning_memory_health_reports_missing_without_creating_database(tmp_path: Path):
    database = tmp_path / "not-created.sqlite3"
    result = build_learning_memory_health(MemoryPath(str(database)))
    assert result["status"] == "MISSING"
    assert result["reason"] == "backup_not_found"
    assert not database.exists()


def test_learning_memory_health_reports_healthy_counts_read_only(tmp_path: Path):
    database = tmp_path / "learning.sqlite3"
    with SQLiteLearningMemory(database) as memory:
        record = memory.put(
            key="health.sample",
            value={"confidence": 0.5},
            department="analysis",
            provenance="replay:health-test",
        )
        memory.put(
            key=record.key,
            value={"confidence": 0.6},
            department="analysis",
            provenance="replay:health-test-update",
            expected_version=record.version,
        )

    before = database.read_bytes()
    result = build_learning_memory_health(MemoryPath(str(database)))
    assert result["status"] == "HEALTHY"
    assert result["integrity"] == "ok"
    assert result["learning_records"] == 1
    assert result["learning_events"] == 2
    assert result["paper_only"] is True
    assert result["orders_submitted"] is False
    assert result["execution_authorized"] is False
    assert database.read_bytes() == before


def test_learning_memory_health_degrades_for_invalid_database(tmp_path: Path):
    database = tmp_path / "invalid.sqlite3"
    database.write_bytes(b"not sqlite")
    result = build_learning_memory_health(MemoryPath(str(database)))
    assert result["status"] == "DEGRADED"
    assert str(result["reason"]).startswith("backup_unreadable:")
