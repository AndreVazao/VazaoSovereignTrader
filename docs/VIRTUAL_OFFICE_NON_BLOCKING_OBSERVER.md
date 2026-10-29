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

## Implemented in the current HTML shell

- Observer fetches use a 2.5-second abort deadline.
- The explicit disconnect action aborts outstanding observer/chat requests and clears the page's in-memory token.
- After successful authentication, the shell polls three read endpoints (runtime state, memory health and market-data health) every 10 seconds. Polling is skipped when the document is hidden, no token is present, or another UI operation is marked busy. This is a bounded request timeout, not a measured CPU/memory isolation guarantee.
- The browser uses same-origin requests, sends the token in the `X-Token` header, uses `cache: no-store` and `credentials: omit`; the token is not deliberately persisted in browser storage or a URL.
- A request abort only cancels the browser's wait. It is **not** proof that a server-side mutation was rolled back; chat failures tell the operator to reconcile state before retrying.
- A reduced-motion media rule disables decorative office-character animations when the operating system requests reduced motion.

## Required validation before claiming isolation

- Unit/integration tests prove the Runtime continues collecting and processing while the office is closed, disconnected, stalled, or returning errors.
- Load tests compare engine scheduling/decision latency with the observer disabled and under saturated observer clients; define thresholds from a measured baseline.
- Test queue saturation, slow clients, repeated disconnects, malformed snapshots, server restarts and revoked credentials.
- Confirm observer endpoints never hold critical locks across network I/O and that event queues are bounded.
- On threshold breach, verify the visual layer degrades/disables and the engine remains healthy. This circuit breaker is an explicit acceptance criterion; it must not be claimed as implemented until code and tests demonstrate it.
- Browser automation and physical Android/PC tests must confirm layout, safe areas, authentication expiry, offline recovery, and no regression in the APK.

## Current status

The HTML shell is a lightweight prototype with bounded/cancellable HTTP requests, a 10-second status poll after authentication, and a reduced-motion rule. These features are not proof of process-level or CPU-level isolation. Automatic rendering degradation, a dedicated observer worker/queue, measured performance budgets, runtime-load comparison tests, and PC/mobile end-to-end measurements remain future implementation/validation steps. Physical PC/mobile testing must be performed when the owner is back at the PC.
