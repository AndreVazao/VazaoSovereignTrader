# Durable research inbox leases

The research inbox remains an append-only JSONL journal for backwards compatibility. New records add optional lease metadata; older records without those fields remain readable.

## Claim and recovery contract

- A worker claims one pending request under an OS-level file lock. The lock serializes claim/read/append operations across threads and processes on Windows and POSIX.
- A claim records a unique worker owner, expiry timestamp and monotonically increasing attempt count. The default lease is five minutes and is bounded to 30 seconds–one hour.
- A worker may complete or release only a request currently leased to its owner. Expired claims can be reclaimed by a later worker.
- After three failed/expired attempts, the request becomes `FAILED`; it is not silently discarded or retried forever.
- Each journal append is flushed and fsynced before the claim/completion call returns.
- Research knowledge publication checks the stable request ID before appending, preventing duplicate knowledge rows when a worker crashes after publishing evidence but before marking the request complete.

## Limits and safety

Leases provide bounded at-least-once processing, not exactly-once execution. A crash can cause a request to be fetched/evaluated again after expiry. Public HTTP reads and local evaluation are repeatable; knowledge publication is deduplicated by request ID. Any future non-idempotent external side effect must not be added to this worker without a separate idempotency design.

The worker remains advisory. A lease cannot authorize exchange access, order placement, fund movement, REAL mode, or strategy promotion. Tests use local synthetic requests and do not connect to exchanges.
