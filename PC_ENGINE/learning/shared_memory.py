"""Local shared learning memory for logical Sovereign Trader departments.

This first implementation is process-local and thread-safe. It is deliberately
not a market-tick store, distributed database, or execution authorization system.
"""
from __future__ import annotations

import math
import threading
import time
from dataclasses import dataclass
from typing import Callable, Iterable


VALID_STATUSES = frozenset({"unverified", "testing", "supported", "rejected", "stale"})


@dataclass(frozen=True)
class LearningRecord:
    key: str
    value: object
    department: str
    provenance: str
    status: str
    confidence: float
    created_at_ns: int
    updated_at_ns: int
    expires_at_ns: int | None
    version: int


@dataclass(frozen=True)
class MemoryEvent:
    key: str
    version: int
    status: str
    event_type: str


class VersionConflict(RuntimeError):
    """Raised when a write was based on an outdated record version."""


class SharedLearningMemory:
    """Fast shared record store with version checks and change notifications.

    Callbacks are invoked after releasing the internal lock. Subscriber failures
    are isolated from the write path. Reads can request a maximum age; expired
    records are returned as stale rather than silently treated as current.
    """

    def __init__(self, *, clock_ns: Callable[[], int] = time.monotonic_ns) -> None:
        self._clock_ns = clock_ns
        self._records: dict[str, LearningRecord] = {}
        self._subscribers: list[Callable[[MemoryEvent], None]] = []
        self._lock = threading.RLock()

    @staticmethod
    def _validate_text(value: str, name: str) -> str:
        cleaned = str(value).strip()
        if not cleaned:
            raise ValueError(f"{name} must be non-empty")
        return cleaned

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

    def _publish(self, event: MemoryEvent, subscribers: Iterable[Callable[[MemoryEvent], None]]) -> None:
        for callback in subscribers:
            try:
                callback(event)
            except Exception:
                # A broken observer must not make a committed write appear to fail.
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
        if ttl_ms is not None and (isinstance(ttl_ms, bool) or int(ttl_ms) < 1):
            raise ValueError("ttl_ms must be a positive integer or None")
        now = self._clock_ns()

        with self._lock:
            previous = self._records.get(key)
            current_version = previous.version if previous else 0
            if expected_version is not None and expected_version != current_version:
                raise VersionConflict(
                    f"expected version {expected_version}, current version is {current_version}"
                )
            version = current_version + 1
            record = LearningRecord(
                key=key,
                value=value,
                department=department,
                provenance=provenance,
                status=status,
                confidence=confidence,
                created_at_ns=previous.created_at_ns if previous else now,
                updated_at_ns=now,
                expires_at_ns=now + int(ttl_ms) * 1_000_000 if ttl_ms is not None else None,
                version=version,
            )
            self._records[key] = record
            subscribers = tuple(self._subscribers)

        self._publish(MemoryEvent(key, version, status, "put"), subscribers)
        return record

    def get(self, key: str, *, max_age_ms: int | None = None) -> LearningRecord | None:
        key = self._validate_text(key, "key")
        now = self._clock_ns()
        if max_age_ms is not None and (isinstance(max_age_ms, bool) or int(max_age_ms) < 0):
            raise ValueError("max_age_ms must be a non-negative integer or None")
        with self._lock:
            record = self._records.get(key)
        if record is None:
            return None

        too_old = max_age_ms is not None and now - record.updated_at_ns > int(max_age_ms) * 1_000_000
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
            records = tuple(self._records.values())
        if status is not None:
            records = tuple(record for record in records if record.status == status)
        return tuple(sorted(records, key=lambda record: record.key))

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
