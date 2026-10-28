# Learning Memory Runtime Integration Gate

**Status: design and acceptance criteria only; not yet wired into SovereignEngine.**

The SQLite adapter is durable, but the live engine must not silently switch stores until lifecycle ownership and failure behavior are tested. This document is the implementation checklist for that next change.

## Required lifecycle

1. Resolve a single owner-private database path from the runtime's existing owner context. Do not place learning state in a temporary directory or share one user's private database with another installation.
2. Construct the store during engine initialization, before research/department workers can publish findings. Preserve the current process-local memory API where consumers still depend on it; introduce an explicit adapter or migration rather than silently changing semantics.
3. Start workers only after the store is ready. A database-open or schema error must be visible in runtime health and must not be reported as successful durable learning.
4. Stop producers before closing the store. On shutdown, stop/join learning-related workers, finish or roll back any active transaction, then close the SQLite connection. Repeated stop calls must be safe.
5. Treat subscriber callbacks as process-local hints only. For other processes, consume the durable event journal or use an explicit IPC mechanism; never promise cross-process notifications from SQLite callbacks.
6. Keep research evidence and learning records separate from execution authority. No stored record may authorize an order, switch PAPER to REAL, or bypass risk, freshness, replay, or human-approval gates.

## Required acceptance tests

- Same key/version written by two independent connections: exactly one commit succeeds and the other receives VersionConflict.
- Close/reopen: records, versions, provenance, TTL metadata, and event history survive.
- Expired or over-age evidence is surfaced as stale and cannot be treated as supported.
- Database open/write failure is surfaced in health; no false 'learning saved' success is emitted.
- Engine stop closes learning resources only after producer workers stop; repeated stop is idempotent.
- Restart recovery uses the same owner-private path and does not mix data between owners.
- PAPER engine smoke and the existing order-authorization tests remain green.
- No REAL exchange action, account provisioning, cloud migration, or live execution is used in these tests.

## Release decision

Do not mark durable learning as production-ready until the adapter is wired into the real engine lifecycle and all acceptance tests pass. Until then, describe it as an implemented SQLite adapter with partial validation, not as the active memory of every department.
