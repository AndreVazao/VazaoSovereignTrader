# Durable Learning Memory (SQLite)

**Status:** SQLite adapter is wired into `SovereignEngine` and the autonomous market-observation path. A verified local backup helper now creates consistent SQLite snapshots and checks integrity/schema before publishing a new backup file. Scheduled backup cadence, retention policy, broader department adoption, and physical restore drills remain follow-up work.

## Why this exists

The original `SharedLearningMemory` is process-local. Its records disappear when the process exits. `SQLiteLearningMemory` provides a durable local store for derived hypotheses, research findings, replay results, validation decisions, and provenance so departments can recover the same versioned knowledge after restart.

## Contract

- Uses SQLite transactions and optimistic `expected_version` checks to prevent stale workers overwriting newer findings.
- Persists record metadata: department, provenance, validation status, confidence, creation/update timestamps, optional TTL, and version.
- Uses wall-clock nanoseconds for stored timestamps so TTL/freshness remains meaningful after restart. Use a monotonic clock only for elapsed measurements inside a running process.
- Persists an append-only change journal; process-local subscriber callbacks are best-effort notifications and are not a cross-process event bus.
- Stores values as JSON. Unsupported objects, NaN, and Infinity are rejected instead of being silently coerced.
- Returns expired or over-age records as `stale`; it never silently promotes an unverified hypothesis.
- Does not store high-frequency market ticks. Raw events and tick streams belong in a dedicated data path; the learning memory should hold derived knowledge and references to reproducible evidence.
- Does not authorize or submit orders and is not a distributed database.
- The engine stores the learning-memory health summary in owner operational state; `order_authority` is explicitly false. Learning records stay `unverified` until a separate validation workflow updates them.

## Minimal use

```python
from PC_ENGINE.learning.sqlite_memory import SQLiteLearningMemory

with SQLiteLearningMemory("PC_ENGINE/data/learning/sovereign-learning.sqlite3") as memory:
    record = memory.put(
        key="temporal.btc-usdt.binance-bingx",
        value={"net_edge_bps": 1.2, "sample_count": 250},
        department="analysis",
        provenance="replay:run-2026-10-20-001",
        status="testing",
        confidence=0.55,
        ttl_ms=60 * 60 * 1000,
    )
```

## Verified local backup

Use `backup_learning_memory(source_path, destination_path)` from `PC_ENGINE.learning.memory_backup` to create a snapshot:

```python
from PC_ENGINE.learning.memory_backup import backup_learning_memory

backup_learning_memory(
    "owners/my-owner/learning/sovereign-learning.sqlite3",
    "backups/sovereign-learning-2026-10-28.sqlite3",
)
```

The helper uses SQLite's online backup API, so the source may remain open and use WAL mode. Before exposing the destination, it runs `PRAGMA integrity_check` and verifies that both `learning_records` and `learning_events` exist. Publication uses an atomic same-filesystem hard link and refuses to overwrite an existing destination. Keep backups in a private owner-controlled directory with appropriate filesystem permissions; this helper does not encrypt backups, schedule them, rotate old copies, or upload them anywhere.

Recovery validation should open the backup with `SQLiteLearningMemory` and verify expected record keys, versions, provenance, statuses and event history before treating it as a usable recovery point. Keep the original database unchanged until the restored copy has been verified. A backup is not a substitute for an independently tested restore procedure.

By default, `SovereignEngine` opens `owners/<owner-id>/learning/sovereign-learning.sqlite3` through `OwnerContext.private_path`; `learning_memory.enabled` can disable it, and `learning_memory.path` can select another owner-private relative path. The same store instance is passed to the autonomous research worker, so new market observations are durably recorded as `unverified` records. A failed memory write is counted and exposed in the worker snapshot without crashing the engine loop. The SQLite connection stays open across ordinary `stop()`/`start()` cycles. The terminal `SovereignEngine.close()` method stops and joins producers before closing it; `PC_ENGINE/main.py` calls this in a `finally` block when the server exits. Do not call `close()` while the engine is expected to restart.

## Remaining operational work

- Define a bounded backup cadence and retention/rotation policy based on available disk space.
- Add backup age/health reporting to runtime operational state without exposing private learning payloads.
- Exercise restore on a separate copy and document a safe operator runbook.
- Validate multi-process writers/recovery and onboard additional departments deliberately.

## Validation boundary

This adapter improves persistence and conflict handling; it does not prove that a market hypothesis is correct or profitable. A finding must still pass data-quality checks, replay without look-ahead, realistic costs/latency, out-of-sample validation, and independent risk review. Stale, missing, or unverified evidence must not enable Rapid-Bet or live execution.
