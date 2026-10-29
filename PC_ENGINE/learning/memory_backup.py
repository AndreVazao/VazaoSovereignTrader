"""Consistent, verified backups for the durable SQLite learning memory.

This utility is intentionally explicit: it never overwrites an existing backup,
never deletes source data, and never enables cloud sync or execution authority.
"""
from __future__ import annotations

import os
import sqlite3
import tempfile
from pathlib import Path


_REQUIRED_TABLES = {"learning_records", "learning_events"}


def backup_learning_memory(
    source_path: str | Path,
    destination_path: str | Path,
) -> Path:
    """Create a consistent SQLite backup and verify it before publishing it.

    SQLite's backup API captures a consistent snapshot even when the source uses
    WAL mode or has another connection open. The completed temporary database is
    integrity-checked and schema-checked before it becomes the destination.
    Existing destinations are rejected so a scheduled backup cannot silently
    destroy an earlier recovery point.
    """
    source = Path(source_path).expanduser()
    destination = Path(destination_path).expanduser()

    if source.resolve() == destination.resolve():
        raise ValueError("backup_destination_must_differ_from_source")
    if not source.exists() or not source.is_file():
        raise FileNotFoundError("learning_memory_source_not_found")
    if destination.exists():
        raise FileExistsError("backup_destination_already_exists")

    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)

    source_db: sqlite3.Connection | None = None
    backup_db: sqlite3.Connection | None = None
    try:
        source_db = sqlite3.connect(str(source), timeout=10.0)
        backup_db = sqlite3.connect(str(temporary), timeout=10.0)
        source_db.backup(backup_db)

        integrity = backup_db.execute("PRAGMA integrity_check").fetchone()
        if integrity is None or integrity[0] != "ok":
            raise sqlite3.DatabaseError("learning_memory_backup_integrity_check_failed")

        tables = {
            row[0]
            for row in backup_db.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        if not _REQUIRED_TABLES.issubset(tables):
            raise sqlite3.DatabaseError("learning_memory_backup_schema_incomplete")

        backup_db.close()
        backup_db = None
        source_db.close()
        source_db = None

        # Hard-link publication is atomic and fails rather than replacing a
        # destination created concurrently by another backup process.
        os.link(temporary, destination)
        temporary.unlink()
        return destination
    finally:
        if backup_db is not None:
            backup_db.close()
        if source_db is not None:
            source_db.close()
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def verify_learning_memory_backup(path: str | Path) -> dict[str, object]:
    """Read-only verification of a backup without modifying or restoring it.

    A missing file is reported as missing; malformed, incomplete, or unreadable
    databases are reported as degraded. This is a diagnostic result only and
    must never be interpreted as permission to overwrite or auto-restore a live
    learning database.
    """
    backup = Path(path).expanduser()
    result: dict[str, object] = {
        "status": "missing",
        "path": str(backup),
        "integrity": None,
        "learning_records": None,
        "learning_events": None,
        "reason": "backup_not_found",
    }
    if not backup.exists() or not backup.is_file():
        return result

    result["status"] = "degraded"
    result["reason"] = "backup_not_verified"
    connection: sqlite3.Connection | None = None
    try:
        # mode=ro prevents diagnostics from creating or modifying the database.
        connection = sqlite3.connect(
            f"{backup.resolve().as_uri()}?mode=ro", uri=True, timeout=5.0
        )
        integrity_row = connection.execute("PRAGMA integrity_check").fetchone()
        integrity = integrity_row[0] if integrity_row else "no_integrity_result"
        result["integrity"] = integrity
        if integrity != "ok":
            result["reason"] = "backup_integrity_check_failed"
            return result

        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        if not _REQUIRED_TABLES.issubset(tables):
            result["reason"] = "backup_schema_incomplete"
            return result

        result["learning_records"] = int(
            connection.execute("SELECT COUNT(*) FROM learning_records").fetchone()[0]
        )
        result["learning_events"] = int(
            connection.execute("SELECT COUNT(*) FROM learning_events").fetchone()[0]
        )
        result["status"] = "healthy"
        result["reason"] = None
        return result
    except (OSError, sqlite3.DatabaseError, ValueError) as exc:
        result["reason"] = f"backup_unreadable:{type(exc).__name__}"
        return result
    finally:
        if connection is not None:
            connection.close()


def restore_learning_memory_backup(
    backup_path: str | Path,
    destination_path: str | Path,
) -> Path:
    """Restore a verified backup to a NEW database path only.

    This is an explicit, offline recovery primitive: it never overwrites an
    existing destination and never replaces a live database automatically.
    The caller is responsible for choosing a separate disposable/recovery path
    and reviewing the result before any operational cutover.
    """
    backup = Path(backup_path).expanduser()
    destination = Path(destination_path).expanduser()
    verification = verify_learning_memory_backup(backup)
    if verification["status"] != "healthy":
        reason = verification.get("reason") or "backup_not_verified"
        raise sqlite3.DatabaseError(f"learning_memory_restore_source_not_healthy:{reason}")
    if backup.resolve() == destination.resolve():
        raise ValueError("restore_destination_must_differ_from_backup")
    if destination.exists():
        raise FileExistsError("restore_destination_already_exists")

    # Reuse the atomic, no-overwrite SQLite snapshot path only after the
    # independent read-only verifier has accepted the backup.
    return backup_learning_memory(backup, destination)
