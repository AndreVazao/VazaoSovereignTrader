# Runtime observer isolation — implementation notes

## Contract

The Virtual Office is optional and has no authority over the Runtime's lifecycle, market decisions, risk controls or execution. A missing browser, slow renderer, disconnected phone, invalid token or failed office request must not pause or stop the engine.

## This increment

- Adds authenticated `GET /observer/summary`, which copies only a small set of primitive status fields under the engine lock. It intentionally avoids `asdict()`, nested snapshots, disk scans, diagnostic aggregation and external I/O.
- Updates the office's normal connect/refresh flow to use the lightweight summary and the dedicated market-data-health endpoint instead of running the heavier operational diagnostics endpoint on every refresh.
- Keeps request deadlines and cancellation from the prior office increment; no polling or animation stream is introduced.
- Adds a route regression assertion that the summary endpoint rejects unauthenticated requests.

## Important boundary

This is a reduction of observer work on the request path, not proof of zero contention. The lightweight endpoint still acquires the engine lock briefly to copy primitive fields. The full `/status` and `/diagnostics` routes remain available for explicit deeper inspection and may perform more work.

The next engineering step is to measure lock wait and engine-cycle latency, and move observer publication to a bounded/coalescing queue or cached snapshot updated outside critical work. Visual consumers must be allowed to drop stale frames. If measured resource or latency budgets are breached, the visual layer should degrade and then disable without changing the Runtime's own safety policy.

## Acceptance tests still required

- Compare engine-cycle/scheduling latency with office clients absent, normal, and saturated.
- Demonstrate that slow observer clients cannot hold engine/risk/market-data locks across serialization or network I/O.
- Exercise queue saturation, browser disconnects, malformed snapshots, server restart and credential revocation.
- Verify a visual circuit breaker disables presentation under pressure while the engine continues safely.
- Complete PC/mobile end-to-end testing when the owner is physically available.

Do not claim full process/CPU isolation until implementation and measurements support it.
