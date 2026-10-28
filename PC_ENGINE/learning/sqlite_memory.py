"""SQLite-backed durable learning memory for Sovereign Trader departments.

Values are JSON documents, not executable objects. Timestamps use wall-clock
nanoseconds so TTL/freshness survives process restarts. This store is for
derived learning/evidence, never high-frequency market ticks or order authority.
"""
from __future__ import annotations

import json
import math
import sqlite3
import threading
import time
from pathlib import Path
from typing import Callable

from PC_ENGINE.learning.shared_memory import (
    VALID_STATUSES,
    LearningRecord,
    MemoryEvent,
    VersionConflict,
)


class SQLiteLearningMemory:
    """Durable, versioned shared memory with an append-only change journal.

    The API intentionally mirrors SharedLearningMemory where practical. Values
    must be JSON-serializable so records can be safely restored after restart.
    Writes use SQLite transactions and optimistic version checks. Subscribers
    are process-local notifications; the event journal is durable.
    """

    def __init__(
        self,
        database_path: str | Path,
        *,
        clock_ns: Callable[[], int] = time.time_ns,
    ) -> None:
        self.database_path = str(database_path)
        if self.database_path != ":memory:":
            Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        self._clock_ns = clock_ns
        self._lock = threading.RLock()
        self._subscribers: list[Callable[[MemoryEvent], None]] = []
        self._connection = sqlite3.connect(
            self.database_path, timeout=10.0, check_same_thread=False
        )
        self._connection.row_factory = sqlite3.Row
        with self._lock:
            self._connection.execute("PRAGMA busy_timeout = 10000")
            self._connection.execute("PRAGMA journal_mode = WAL")
            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS learning_records (
                    key TEXT PRIMARY KEY,
                    value_json TEXT NOT NULL,
                    department TEXT NOT NULL,
                    provenance TEXT NOT NULL,
                    status TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    created_at_ns INTEGER NOT NULL,
                    updated_at_ns INTEGER NOT NULL,
                    expires_at_ns INTEGER,
                    version INTEGER NOT NULL CHECK (version >= 1)
                );
                CREATE TABLE IF NOT EXISTS learning_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    created_at_ns INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_learning_events_key_id
                    ON learning_events(key, event_id);
                """
            )

    @staticmethod
    def _validate_text(value: str, name: str) -> str:
        cleaned = str(value).strip()
        if not cleaned:
            raise ValueError(f"{name} must be non-empty")
        return cleaned

    @staticmethod
    def _decode(row: sqlite3.Row) -> LearningRecord:
        return LearningRecord(
            key=row["key"],
            value=json.loads(row["value_json"]),
            department=row["department"],
            provenance=row["provenance"],
            status=row["status"],
            confidence=float(row["confidence"]),
            created_at_ns=int(row["created_at_ns"]),
            updated_at_ns=int(row["updated_at_ns"]),
            expires_at_ns=(
                int(row["expires_at_ns"]) if row["expires_at_ns"] is not None else None
            ),
            version=int(row["version"]),
        )

    def subscribe(self, callback: Callable[[MemoryEvent], None]) -> Callable[[], None]:
        if not callable(callback):
            raise TypeError("callback must be callable")
        with self._lock:
            self._subscribers.append(callback)

        def unsubscribe() -> None:
            with self._lock:
                if callback in self._subscribers:
                    self._subscribers.remove(callback)

        return unsubscribe

    @staticmethod
    def _publish(event: MemoryEvent, subscribers: tuple[Callable[[MemoryEvent], None], ...]) -> None:
        for callback in subscribers:
            try:
                callback(event)
            except Exception:
                # Observer errors must not make a committed transaction look failed.
                continue

    def put(
        self,
        *,
        key: str,
        value: object,
        department: str,
        provenance: str,
        status: str = "unverified",
        confidence: float = 0.0,
        ttl_ms: int | None = None,
        expected_version: int | None = None,
    ) -> LearningRecord:
        key = self._validate_text(key, "key")
        department = self._validate_text(department, "department")
        provenance = self._validate_text(provenance, "provenance")
        status = self._validate_text(status, "status").lower()
        if status not in VALID_STATUSES:
            raise ValueError("unsupported validation status")
        confidence = float(confidence)
        if not math.isfinite(confidence) or not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be finite and between 0 and 1")
        if ttl_ms is not None and (
            isinstance(ttl_ms, bool) or not isinstance(ttl_ms, int) or ttl_ms < 1
        ):
            raise ValueError("ttl_ms must be a positive integer or None")
        if expected_version is not None and (
            isinstance(expected_version, bool)
            or not isinstance(expected_version, int)
            or expected_version < 0
        ):
            raise ValueError("expected_version must be a non-negative integer or None")
        try:
            value_json = json.dumps(
                value, ensure_ascii=False, allow_nan=False, separators=(",", ":")
            )
        except (TypeError, ValueError) as exc:
            raise ValueError("value must be JSON-serializable without NaN or Infinity") from exc

        now = int(self._clock_ns())
        with self._lock:
            connection = self._connection
            connection.execute("BEGIN IMMEDIATE")
            try:
                row = connection.execute(
                    "SELECT * FROM learning_records WHERE key = ?", (key,)
                ).fetchone()
                previous = self._decode(row) if row is not None else None
                current_version = previous.version if previous else 0
                if expected_version is not None and expected_version != current_version:
                    raise VersionConflict(
                        f"expected version {expected_version}, current version is {current_version}"
                    )
                version = current_version + 1
                record = LearningRecord(
                    key=key,
                    value=json.loads(value_json),
                    department=department,
                    provenance=provenance,
                    status=status,
                    confidence=confidence,
                    created_at_ns=previous.created_at_ns if previous else now,
                    updated_at_ns=now,
                    expires_at_ns=now + ttl_ms * 1_000_000 if ttl_ms is not None else None,
                    version=version,
                )
                connection.execute(
                    """
                    INSERT INTO learning_records
                    (key, value_json, department, provenance, status, confidence,
                     created_at_ns, updated_at_ns, expires_at_ns, version)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET
                      value_json=excluded.value_json,
                      department=excluded.department,
                      provenance=excluded.provenance,
                      status=excluded.status,
                      confidence=excluded.confidence,
                      created_at_ns=excluded.created_at_ns,
                      updated_at_ns=excluded.updated_at_ns,
                      expires_at_ns=excluded.expires_at_ns,
                      version=excluded.version
                    """,
                    (
                        record.key, value_json, record.department, record.provenance,
                        record.status, record.confidence, record.created_at_ns,
                        record.updated_at_ns, record.expires_at_ns, record.version,
                    ),
                )
                connection.execute(
                    "INSERT INTO learning_events(key, version, status, event_type, created_at_ns) "
                    "VALUES (?, ?, ?, 'put', ?)",
                    (key, version, status, now),
                )
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            subscribers = tuple(self._subscribers)

        self._publish(MemoryEvent(key, version, status, "put"), subscribers)
        return record

    def get(self, key: str, *, max_age_ms: int | None = None) -> LearningRecord | None:
        key = self._validate_text(key, "key")
        if max_age_ms is not None and (
            isinstance(max_age_ms, bool) or not isinstance(max_age_ms, int) or max_age_ms < 0
        ):
            raise ValueError("max_age_ms must be a non-negative integer or None")
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM learning_records WHERE key = ?", (key,)
            ).fetchone()
        if row is None:
            return None
        record = self._decode(row)
        now = int(self._clock_ns())
        too_old = max_age_ms is not None and now - record.updated_at_ns > max_age_ms * 1_000_000
        expired = record.expires_at_ns is not None and now >= record.expires_at_ns
        if (too_old or expired) and record.status != "stale":
            return LearningRecord(**{**record.__dict__, "status": "stale"})
        return record

    def list_records(self, *, status: str | None = None) -> tuple[LearningRecord, ...]:
        if status is not None:
            status = self._validate_text(status, "status").lower()
            if status not in VALID_STATUSES:
                raise ValueError("unsupported validation status")
        with self._lock:
            rows = self._connection.execute(
                "SELECT * FROM learning_records ORDER BY key"
            ).fetchall()
        now = int(self._clock_ns())
        records: list[LearningRecord] = []
        for row in rows:
            record = self._decode(row)
            if record.expires_at_ns is not None and now >= record.expires_at_ns:
                if record.status != "stale":
                    record = LearningRecord(**{**record.__dict__, "status": "stale"})
            if status is None or record.status == status:
                records.append(record)
        return tuple(records)

    def mark_stale(self, key: str, *, expected_version: int | None = None) -> LearningRecord:
        current = self.get(key)
        if current is None:
            raise KeyError(key)
        return self.put(
            key=current.key,
            value=current.value,
            department=current.department,
            provenance=current.provenance,
            status="stale",
            confidence=current.confidence,
            expected_version=current.version if expected_version is None else expected_version,
        )

    def list_events(self, *, key: str | None = None, limit: int = 100) -> tuple[MemoryEvent, ...]:
        """Return newest durable change events, oldest-first within the returned page."""
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("limit must be a positive integer")
        with self._lock:
            if key is None:
                rows = self._connection.execute(
                    "SELECT key, version, status, event_type FROM learning_events "
                    "ORDER BY event_id DESC LIMIT ?", (limit,)
                ).fetchall()
            else:
                key = self._validate_text(key, "key")
                rows = self._connection.execute(
                    "SELECT key, version, status, event_type FROM learning_events "
                    "WHERE key = ? ORDER BY event_id DESC LIMIT ?", (key, limit)
                ).fetchall()
        return tuple(
            MemoryEvent(row["key"], int(row["version"]), row["status"], row["event_type"])
            for row in reversed(rows)
        )

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def __enter__(self) -> "SQLiteLearningMemory":
        return self

    def __exit__(self, _exc_type: object, _exc: object, _traceback: object) -> None:
        self.close()
