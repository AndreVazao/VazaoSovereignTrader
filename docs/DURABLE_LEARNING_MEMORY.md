# Durable Learning Memory (SQLite)

**Status:** SQLite adapter is wired into `SovereignEngine` and the autonomous market-observation path. Runtime tests cover owner-private placement, persistence of unverified observations, and opt-out behavior. Broader department adoption and operational backup/retention policy remain follow-up work.

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

By default, `SovereignEngine` opens `owners/<owner-id>/learning/sovereign-learning.sqlite3` through `OwnerContext.private_path`; `learning_memory.enabled` can disable it, and `learning_memory.path` can select another owner-private relative path. The same store instance is passed to the autonomous research worker, so new market observations are durably recorded as `unverified` records. A failed memory write is counted and exposed in the worker snapshot without crashing the engine loop. The SQLite connection is process-lifetime state; a terminal process shutdown closes it through the operating system. Do not call `close()` while the engine is expected to restart. Backups, retention policy, multi-process shared writers, and additional department consumers remain follow-up work.

## Validation boundary

This adapter improves persistence and conflict handling; it does not prove that a market hypothesis is correct or profitable. A finding must still pass data-quality checks, replay without look-ahead, realistic costs/latency, out-of-sample validation, and independent risk review. Stale, missing, or unverified evidence must not enable Rapid-Bet or live execution.
