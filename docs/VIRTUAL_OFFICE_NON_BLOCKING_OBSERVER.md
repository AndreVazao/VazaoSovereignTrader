# Virtual Office: non-blocking observer contract

## Authority boundary

The Sovereign Trader Runtime is the sole authority for engine lifecycle, market decisions, risk limits, orders and persisted trading state. The Virtual Office is an optional observer/control client. It must never be a prerequisite for the Runtime to start, collect data, research, evaluate risk, or react.

The office is allowed to disappear without affecting the Runtime. Closing the browser, losing LAN/Tailscale, an invalid token, a stalled browser, failed rendering, malformed responses, or an office deployment failure must not stop or pause the engine.

## Required architecture

1. **One engine, many clients.** Cockpit and office attach to the already-running Runtime. A UI request must never instantiate a second engine.
2. **Publish, do not wait.** Runtime state is exposed through bounded snapshots/events. Engine hot paths must not synchronously wait for browser delivery, animation, rendering, dashboard refresh, remote acknowledgement or a UI database write.
3. **Separate the critical path.** UI serialization, event fan-out, chart aggregation and virtual-character simulation belong in a low-priority observer path or separate process/worker. They may consume only bounded queues and precomputed snapshots; they must not hold engine, risk, market-data or order locks while doing rendering/serialization/network I/O.
4. **Backpressure is lossy for visuals, not for the engine.** Coalesce superseded status updates and drop visual frames/events when the consumer falls behind. Never backpressure the engine to preserve animation fidelity. Audit/risk events that require durable handling must use their own bounded, explicit persistence path—not the visual queue.
5. **Fail closed on presentation.** If observer queue depth, CPU budget, memory budget, API latency or engine scheduling health crosses a configured limit, reduce update frequency and graphical fidelity, then disable the visual layer if the limit persists. The Runtime keeps operating under its own risk policy. UI degradation must not relax risk checks or authorize trading.
6. **Read-only by default.** Observation endpoints are authenticated, read-only and rate-limited. Commands use separate server-side scopes and confirmation/guard paths. A browser timeout after a mutation means “outcome unknown”; never replay automatically.
7. **No secret persistence.** Tokens stay in memory and travel in headers, never in URLs, logs or browser storage. Requests use same-origin endpoints, `cache: no-store`, and no ambient credentials.
8. **No invented health.** Missing, stale, malformed or timed-out values render as unknown/stale/offline, not zero or a plausible default.

## Implemented in this increment

- The office's fetch helper gives each observer request a 2.5-second abort deadline.
- The explicit disconnect action aborts outstanding observer/chat requests and clears the page's in-memory token.
- No background polling or visual subscription was introduced; refresh remains operator-triggered. This avoids creating a new continuous request load while the office is being hardened.
- A request abort only cancels the browser's wait. It is **not** proof that a server-side mutation was rolled back; chat failures continue to tell the operator to reconcile state before retrying.

## Required validation before claiming isolation

- Unit/integration tests prove the Runtime continues collecting and processing while the office is closed, disconnected, stalled, or returning errors.
- Load tests compare engine scheduling/decision latency with the observer disabled and under saturated observer clients; define thresholds from a measured baseline.
- Test queue saturation, slow clients, repeated disconnects, malformed snapshots, server restarts and revoked credentials.
- Confirm observer endpoints never hold critical locks across network I/O and that event queues are bounded.
- On threshold breach, verify the visual layer degrades/disables and the engine remains healthy. This circuit breaker is an explicit acceptance criterion; it must not be claimed as implemented until code and tests demonstrate it.

## Current status

The current HTML shell is a lightweight prototype and its HTTP reads are bounded/cancellable. This is not yet proof of process-level or CPU-level isolation. Automatic rendering degradation, a dedicated observer worker/queue, performance budgets and PC/mobile end-to-end measurements remain future implementation/validation steps. Physical PC/mobile testing must be performed when the owner is back at the PC.
