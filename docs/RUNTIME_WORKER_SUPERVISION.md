# Runtime worker supervision

## Research worker

The autonomous research worker is auxiliary and non-authoritative. Its failure must not grant trading permissions, change execution mode, or trigger an order.

The worker exposes a small in-process supervision snapshot:
- heartbeat timestamp, refreshed at the beginning and end of each polling iteration;
- last successful iteration timestamp;
- last exception type (never the exception message or source payload);
- completed polling iteration count.

While the engine loop is active, `SovereignEngine` records the worker's liveness in `state.operational.research_worker_supervision`. The state is one of `NOT_STARTED`, `STARTING`, `RUNNING`, `STALE`, `FAILED`, `STOPPED`, or `DISABLED`. A heartbeat older than the larger of 10 seconds or three configured polling intervals is marked `STALE`.

This layer is observability only. It deliberately does not restart a dead worker automatically: a process may have stopped while an inbox item was being updated, and automatic restart without a durable claim/lease protocol could duplicate or strand work. It also does not block the trading engine because research is non-critical. Any future restart policy must first add durable task leases, idempotent result publication, bounded retries, and crash-recovery tests.

## Safety boundary

- Research output remains advisory evidence; it cannot authorize execution.
- Worker failure is visible but is not a signal to retry any exchange operation.
- Engine shutdown supervision remains responsible for joining all producers before closing durable learning storage.
- A stale heartbeat indicates a potentially blocked worker, not proof of a process deadlock.
- Tests use synthetic local workers and do not connect to exchanges or submit orders.
