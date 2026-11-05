from __future__ import annotations

import json
import sqlite3
import subprocess
import sys

import pytest

from PC_ENGINE.learning.memory_backup import (
    backup_learning_memory,
    verify_learning_memory_backup,
    restore_learning_memory_backup,
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
    assert result["status"] == "healthy"
    assert result["path"] == str(destination)
    assert result["integrity"] == "ok"
    assert result["learning_records"] == 1
    assert result["learning_events"] == 2
    assert len(result["checksum"]) == 64
    assert result["manifest_status"] == "verified"
    assert result["reason"] is None
    assert destination.read_bytes() == before
    assert destination.with_name(destination.name + ".manifest.json").is_file()


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


def test_restore_creates_verified_copy_at_new_path_and_preserves_history(tmp_path):
    source = tmp_path / "live" / "learning.sqlite3"
    backup = tmp_path / "backups" / "learning.sqlite3"
    restored_path = tmp_path / "recovery-test" / "restored.sqlite3"
    with SQLiteLearningMemory(source) as memory:
        first = memory.put(
            key="restore.record",
            value={"revision": 1},
            department="analysis",
            provenance="replay:restore-test",
        )
        memory.put(
            key=first.key,
            value={"revision": 2},
            department="analysis",
            provenance="replay:restore-test-update",
            expected_version=first.version,
        )
        backup_learning_memory(source, backup)

    before_backup = backup.read_bytes()
    assert restore_learning_memory_backup(backup, restored_path) == restored_path
    assert backup.read_bytes() == before_backup
    assert verify_learning_memory_backup(restored_path)["status"] == "healthy"

    with SQLiteLearningMemory(restored_path) as restored:
        record = restored.get("restore.record")
        assert record is not None
        assert record.value == {"revision": 2}
        assert record.version == 2
        assert [(event.version, event.event_type) for event in restored.list_events(
            key="restore.record"
        )] == [(1, "put"), (2, "put")]


def test_restore_refuses_to_overwrite_existing_destination(tmp_path):
    source = tmp_path / "learning.sqlite3"
    backup = tmp_path / "backup.sqlite3"
    destination = tmp_path / "recovery.sqlite3"
    with SQLiteLearningMemory(source) as memory:
        memory.put(
            key="restore.safe",
            value={"safe": True},
            department="test",
            provenance="test",
        )
    backup_learning_memory(source, backup)
    destination.write_bytes(b"preserve existing recovery target")

    with pytest.raises(FileExistsError, match="restore_destination_already_exists"):
        restore_learning_memory_backup(backup, destination)
    assert destination.read_bytes() == b"preserve existing recovery target"


def test_restore_rejects_unhealthy_backup_without_creating_destination(tmp_path):
    backup = tmp_path / "corrupt.sqlite3"
    destination = tmp_path / "restored.sqlite3"
    backup.write_bytes(b"not a sqlite database")

    with pytest.raises(sqlite3.DatabaseError, match="restore_source_not_healthy"):
        restore_learning_memory_backup(backup, destination)
    assert not destination.exists()


def test_restore_rejects_same_backup_and_destination_path(tmp_path):
    source = tmp_path / "learning.sqlite3"
    with SQLiteLearningMemory(source) as memory:
        memory.put(
            key="restore.same-path",
            value={"safe": True},
            department="test",
            provenance="test",
        )
    backup_learning_memory(source, source.with_name("backup.sqlite3"))
    backup = source.with_name("backup.sqlite3")

    with pytest.raises(ValueError, match="restore_destination_must_differ_from_backup"):
        restore_learning_memory_backup(backup, backup)


def test_backup_verification_detects_checksum_tampering_and_restore_refuses_it(tmp_path):
    source = tmp_path / "learning.sqlite3"
    backup = tmp_path / "backup.sqlite3"
    destination = tmp_path / "recovery.sqlite3"
    with SQLiteLearningMemory(source) as memory:
        memory.put(key="checksum.protected", value={"safe": True}, department="test", provenance="test")
        backup_learning_memory(source, backup)

    with backup.open("ab") as stream:
        stream.write(b"tampered")

    result = verify_learning_memory_backup(backup)
    assert result["status"] == "degraded"
    assert result["manifest_status"] == "mismatch"
    assert result["reason"] == "backup_checksum_mismatch"
    with pytest.raises(sqlite3.DatabaseError, match="restore_source_not_healthy"):
        restore_learning_memory_backup(backup, destination)
    assert not destination.exists()


def test_backup_verification_rejects_invalid_manifest(tmp_path):
    source = tmp_path / "learning.sqlite3"
    backup = tmp_path / "backup.sqlite3"
    with SQLiteLearningMemory(source) as memory:
        memory.put(key="manifest.invalid", value={"ok": True}, department="test", provenance="test")
        backup_learning_memory(source, backup)

    backup.with_name(backup.name + ".manifest.json").write_text("not-json", encoding="utf-8")
    result = verify_learning_memory_backup(backup)
    assert result["status"] == "degraded"
    assert result["manifest_status"] == "invalid"
    assert result["reason"] == "backup_manifest_invalid"


def _run_backup_cli(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "PC_ENGINE.learning.memory_backup", *arguments],
        capture_output=True,
        text=True,
        check=False,
    )


def test_operator_cli_backup_and_verify_are_explicit_and_machine_readable(tmp_path):
    source = tmp_path / "owner" / "learning.sqlite3"
    backup = tmp_path / "backups" / "learning.snapshot.sqlite3"
    with SQLiteLearningMemory(source) as memory:
        memory.put(
            key="cli.record", value={"safe": True}, department="test", provenance="cli-test"
        )

    created = _run_backup_cli(
        "backup", "--source", str(source), "--destination", str(backup)
    )
    assert created.returncode == 0, created.stderr
    payload = json.loads(created.stdout)
    assert payload["operation"] == "backup"
    assert payload["verification"]["status"] == "healthy"
    assert backup.is_file()
    assert backup.with_name(backup.name + ".manifest.json").is_file()

    verified = _run_backup_cli("verify", "--backup", str(backup))
    assert verified.returncode == 0, verified.stderr
    assert json.loads(verified.stdout)["manifest_status"] == "verified"


def test_operator_cli_restore_requires_a_new_destination(tmp_path):
    source = tmp_path / "owner" / "learning.sqlite3"
    backup = tmp_path / "backups" / "learning.sqlite3"
    destination = tmp_path / "recovery" / "restored.sqlite3"
    with SQLiteLearningMemory(source) as memory:
        memory.put(
            key="cli.restore", value={"revision": 4}, department="test", provenance="cli-test"
        )
    assert _run_backup_cli(
        "backup", "--source", str(source), "--destination", str(backup)
    ).returncode == 0

    restored = _run_backup_cli(
        "restore", "--backup", str(backup), "--destination", str(destination)
    )
    assert restored.returncode == 0, restored.stderr
    payload = json.loads(restored.stdout)
    assert payload["operation"] == "restore"
    assert payload["verification"]["status"] == "healthy"
    with SQLiteLearningMemory(destination) as memory:
        assert memory.get("cli.restore").value == {"revision": 4}


def test_operator_cli_returns_nonzero_for_corrupt_backup(tmp_path):
    corrupt = tmp_path / "corrupt.sqlite3"
    corrupt.write_bytes(b"not sqlite")
    result = _run_backup_cli("verify", "--backup", str(corrupt))
    assert result.returncode == 2
    assert json.loads(result.stdout)["status"] == "degraded"
