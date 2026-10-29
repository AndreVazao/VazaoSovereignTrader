# Learning Memory Runtime Integration Gate

**Status: initial engine integration implemented; broad production rollout remains gated.**

`SovereignEngine` now opens an owner-private SQLite store and passes the same instance to `AutonomousResearchWorker`. New autonomous market observations are persisted as `unverified` records. Runtime tests cover private path placement, opt-out, write failure reporting, and terminal close ordering. This is the first consumer, not yet a claim that every department uses the store.

## Required lifecycle

1. Resolve a single owner-private database path from the runtime's existing owner context. Do not place learning state in a temporary directory or share one user's private database with another installation.
2. **Implemented for the first consumer:** construct the store during engine initialization, before research workers start, and inject it into the autonomous research worker. Keep existing process-local memory APIs unchanged for consumers not yet migrated.
3. **Implemented:** engine operational state reports READY, DISABLED, or UNAVAILABLE. Write failures are counted in the worker snapshot and do not crash the engine loop or claim a successful durable write.
4. **Implemented for terminal shutdown:** `SovereignEngine.close()` requests stop, joins engine/research workers, and closes SQLite only after they exit. If a worker remains alive after bounded joins, closing is deferred rather than racing an active producer. Ordinary `stop()` remains restartable and does not close the store. The PC server calls `close()` in its `finally` shutdown path.
5. Treat subscriber callbacks as process-local hints only. For other processes, consume the durable event journal or use an explicit IPC mechanism; never promise cross-process notifications from SQLite callbacks.
6. Keep research evidence and learning records separate from execution authority. No stored record may authorize an order, switch PAPER to REAL, or bypass risk, freshness, replay, or human-approval gates.

## Required acceptance tests

- Same key/version written by two independent connections: exactly one commit succeeds and the other receives VersionConflict.
- Close/reopen: records, versions, provenance, TTL metadata, and event history survive.
- Expired or over-age evidence is surfaced as stale and cannot be treated as supported.
- Database open/write failure is surfaced in health; no false 'learning saved' success is emitted.
- Terminal engine close joins producer workers before closing learning resources; repeated close is idempotent, and start is blocked after terminal close.
- Restart recovery uses the same owner-private path and does not mix data between owners.
- PAPER engine smoke and the existing order-authorization tests remain green.
- No REAL exchange action, account provisioning, cloud migration, or live execution is used in these tests.

## Release decision

Do not mark durable learning as production-ready for every department yet. Initial runtime wiring and lifecycle handling are implemented, but broader department adoption, backup/retention policy, multi-process writer/recovery tests, and evidence of the cloud database/key-lifecycle gates remain outstanding. Describe it as active for autonomous research observations only, not as the active memory of every department.


## Read-only health endpoint

The authenticated local API now exposes `GET /learning-memory/health` under the existing `read_private_state` scope. It reports storage integrity/schema status and record/event counts using a separate read-only SQLite connection. It does not create a missing database, repair a damaged database, or trigger restore.

- `HEALTHY`: the configured durable SQLite file passed integrity and required-table checks.
- `DEGRADED`: the file exists but cannot be verified or has an incomplete schema.
- `MISSING`: the configured file is absent.
- `NOT_CONFIGURED`: the engine has no durable learning-memory instance.
- `UNKNOWN`: the path cannot be inspected safely (including an in-memory database).

This endpoint diagnoses durable storage only. It does not prove the learning worker is running, every department is connected, evidence is useful/fresh, or the whole engine is healthy. Its response explicitly remains PAPER-only and never authorizes execution.
