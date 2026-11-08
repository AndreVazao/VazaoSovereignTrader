# Bounded iteration for durable learning memory

`SQLiteLearningMemory.iter_records()` provides an incremental, keyset-paginated read path for diagnostics, exports and maintenance tasks that need to inspect the durable learning store without loading every row into memory at once.

- Default page size: 128 records; callers may choose a smaller or larger positive integer.
- Pagination uses the stable primary key (`key`) and `key > last_key`, avoiding large OFFSET scans.
- Expired records are surfaced as `stale` consistently with `list_records()`; optional status filtering is applied after expiry classification.
- Each page is fetched while holding the store lock; the lock is released before records are yielded to the caller.
- Traversal is weakly consistent, not a database-wide snapshot. Concurrent updates may be observed with their newer values; keys inserted before the current cursor are not seen until a subsequent traversal.
- The existing `list_records()` API remains unchanged for callers that explicitly need a fully materialized tuple.

Use the iterator for bounded processing:

```python
for record in memory.iter_records(status="supported", batch_size=64):
    process(record)
```

This change is limited to durable derived learning records. It does not affect high-frequency Market Data, Radar observation, PAPER bookkeeping, order authority, risk limits or PAPER/REAL permissions. It does not claim to certify the full engine lifecycle.
