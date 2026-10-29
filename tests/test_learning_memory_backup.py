from __future__ import annotations

import sqlite3

import pytest

from PC_ENGINE.learning.memory_backup import (
    backup_learning_memory,
    verify_learning_memory_backup,
)
from PC_ENGINE.learning.sqlite_memory import SQLiteLearningMemory


def test_backup_preserves_records_and_event_history_while_source_is_open(tmp_path):
    source = tmp_path / "owner" / "learning.sqlite3"
    destination = tmp_path / "backups" / "learning.snapshot.sqlite3"
    with SQLiteLearningMemory(source) as memory:
        first = memory.put(
            key="market.edge.btc-usdt",
            value={"net_edge_bps": 1.25},
            department="analysis",
            provenance="replay:backup-test",
            status="unverified",
            confidence=0.4,
        )
        memory.put(
            key=first.key,
            value={"net_edge_bps": 1.5},
            department="analysis",
            provenance="replay:backup-test-update",
            status="testing",
            confidence=0.6,
            expected_version=first.version,
        )

        result = backup_learning_memory(source, destination)
        assert result == destination
        # The live source remains usable after the backup completes.
        memory.put(
            key="market.edge.eth-usdt",
            value={"net_edge_bps": 0.8},
            department="analysis",
            provenance="replay:source-after-backup",
        )

    with SQLiteLearningMemory(destination) as restored:
        record = restored.get("market.edge.btc-usdt")
        assert record is not None
        assert record.value == {"net_edge_bps": 1.5}
        assert record.version == 2
        assert record.status == "testing"
        assert record.provenance == "replay:backup-test-update"
        assert [(event.version, event.event_type) for event in restored.list_events(
            key="market.edge.btc-usdt"
        )] == [(1, "put"), (2, "put")]
        assert restored.get("market.edge.eth-usdt") is None


def test_backup_refuses_to_overwrite_existing_destination(tmp_path):
    source = tmp_path / "learning.sqlite3"
    destination = tmp_path / "backup.sqlite3"
    with SQLiteLearningMemory(source) as memory:
        memory.put(
            key="test.record",
            value={"safe": True},
            department="test",
            provenance="test",
        )

    destination.write_bytes(b"keep this recovery point")
    with pytest.raises(FileExistsError, match="backup_destination_already_exists"):
        backup_learning_memory(source, destination)
    assert destination.read_bytes() == b"keep this recovery point"


def test_backup_rejects_same_source_and_destination(tmp_path):
    source = tmp_path / "learning.sqlite3"
    with SQLiteLearningMemory(source):
        pass

    with pytest.raises(ValueError, match="backup_destination_must_differ_from_source"):
        backup_learning_memory(source, source)


def test_backup_rejects_corrupt_or_non_learning_sqlite_database(tmp_path):
    source = tmp_path / "not-learning.sqlite3"
    destination = tmp_path / "backup.sqlite3"
    connection = sqlite3.connect(source)
    connection.execute("CREATE TABLE unrelated (value TEXT)")
    connection.commit()
    connection.close()

    with pytest.raises(sqlite3.DatabaseError, match="learning_memory_backup_schema_incomplete"):
        backup_learning_memory(source, destination)
    assert not destination.exists()
    assert list(tmp_path.glob(".backup.sqlite3.*.tmp")) == []


def test_backup_verification_reports_healthy_counts_without_modifying_file(tmp_path):
    source = tmp_path / "learning.sqlite3"
    destination = tmp_path / "backup.sqlite3"
    with SQLiteLearningMemory(source) as memory:
        record = memory.put(
            key="verified.record",
            value={"safe": True},
            department="test",
            provenance="replay:verification-test",
        )
        memory.put(
            key=record.key,
            value={"safe": True, "revision": 2},
            department="test",
            provenance="replay:verification-test-update",
            expected_version=record.version,
        )
        backup_learning_memory(source, destination)

    before = destination.read_bytes()
    result = verify_learning_memory_backup(destination)
    assert result == {
        "status": "healthy",
        "path": str(destination),
        "integrity": "ok",
        "learning_records": 1,
        "learning_events": 2,
        "reason": None,
    }
    assert destination.read_bytes() == before


def test_backup_verification_distinguishes_missing_from_degraded(tmp_path):
    missing = verify_learning_memory_backup(tmp_path / "missing.sqlite3")
    assert missing["status"] == "missing"
    assert missing["reason"] == "backup_not_found"

    malformed = tmp_path / "malformed.sqlite3"
    malformed.write_bytes(b"not a sqlite database")
    degraded = verify_learning_memory_backup(malformed)
    assert degraded["status"] == "degraded"
    assert str(degraded["reason"]).startswith("backup_unreadable:")
    assert degraded["learning_records"] is None


def test_backup_verification_reports_incomplete_schema_as_degraded(tmp_path):
    incomplete = tmp_path / "incomplete.sqlite3"
    with sqlite3.connect(incomplete) as connection:
        connection.execute("CREATE TABLE unrelated (value TEXT)")

    result = verify_learning_memory_backup(incomplete)
    assert result["status"] == "degraded"
    assert result["integrity"] == "ok"
    assert result["reason"] == "backup_schema_incomplete"
