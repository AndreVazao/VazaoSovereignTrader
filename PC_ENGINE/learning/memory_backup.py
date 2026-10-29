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
