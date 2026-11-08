# Remote conversational cockpit — product requirements and current gates

**Updated:** 2026-11-08  
**Status:** requirements recovered; end-to-end remote operation is not certified.

## Mission

The Sovereign Trader must keep its headless PC brain operating while the owner can observe it and request research from an Android phone, including when away from home for extended periods. The mobile cockpit is a client, not a second trading engine. VST remains separate from DGM-MAT in identity, credentials, data, permissions and runtime.

## Authority boundaries

- `PC_ENGINE` is authoritative for market data, task state, risk, persistence, readiness and any future execution.
- Android/desktop cockpit clients display verified state and submit authenticated requests through a versioned local API.
- Closing, suspending or crashing the cockpit must not stop the headless brain or weaken its risk controls.
- Chat text, notifications, visual animations and a discovered opportunity cannot authorize a financial action.
- PAPER/read-only remains the operating mode. No automatic promotion to REAL.

## Capabilities required

1. Submit natural-language research requests and receive a durable task ID.
2. Inspect task state, timestamps, evidence, sources, blockers and completion reports.
3. View collector health, market-data freshness, Radar state, PAPER status and Learning Vault health.
4. Receive persistent remote notifications for failures, blocked tasks and approvals.
5. Resume after network changes, phone sleep, PC restart or app reinstall without losing task history or duplicating actions.
6. Display explicit `UNKNOWN`, `STALE`, `OFFLINE` and `BLOCKED` states rather than inventing successful activity.
7. Provide secure approval forms for specifically authorized actions only after all existing readiness and risk gates have passed.

## Authentication and sensitive data

- Never place passwords, API secrets, MFA codes, recovery codes or private account data in chat history, logs, push notifications or public rendezvous metadata.
- Credentials must be entered through a dedicated secure form and delivered only to the authorized local connector.
- Bind every session and approval to the owner, device, exact action, parameters, expiry and one-time nonce. Support revocation and replay rejection.
- An approval must show venue, instrument, side, quantity, order type, estimated costs/exposure, expiry and current risk state. This does not itself bypass the Risk Engine, RealModeGuard or readiness checks.
- Treat timeouts and ambiguous external outcomes as unknown; reconcile before any retry. Never blindly repeat orders, cancellations or transfers.
- Orders, configuration/risk changes, withdrawals and transfers are distinct actions with separate authorization.

## Connectivity design

- Prefer private authenticated connectivity (Tailscale is the preferred direct path) for phone-to-PC communication.
- Vercel may be used as an optional, low-data rendezvous/discovery service only. It is not the trading engine, execution plane, durable task store or authority for owner identity.
- Never expose the local API directly to the public Internet. The local API currently listens at `http://127.0.0.1:8765`; its local token is a secret and must not be published or embedded in source.
- Treat IP addresses as temporary routing hints, never as identities or authorization.
- Discovery records must be owner-scoped, signed/authenticated, short-lived, revocable and rate-limited. They must not contain exchange credentials, balances, orders, positions or private research.
- Offline rendezvous, stale leases, Vercel limits or Tailscale unavailability must not block the local market-data and PAPER loops.

## Multi-user and shared learning

Private data is isolated per owner: exchange credentials, balances, positions, orders, fills, strategies, risk settings, logs, diagnostics and device sessions. Cross-owner sharing is limited to explicitly approved, sanitized research artifacts with canonical payload digests, verified provenance, compatibility/version information, timestamps and validation metadata. Imported artifacts are research inputs only; they cannot directly change a live strategy or enable REAL.

The repository contains signed/canonical provenance code and cross-organization verification paths, but this document does not claim that a production database, organization enrollment or live multi-user deployment is configured and operational.

## Current implementation evidence

- Local runtime API contract and health/status endpoints exist in the PC runtime.
- Runtime state, task processing and durable Learning Vault are being developed and tested in the headless engine.
- Android cockpit and offline office prototype exist; the office demo is deliberately disconnected from the brain and does not claim to display live agent activity.
- The Windows installer has passed CI lifecycle checks, including upgrade and Learning Vault preservation.

## Acceptance gates still required

- [ ] Pair an Android device to the correct PC owner using private authenticated connectivity.
- [ ] Verify phone-to-PC health, status, task submission and task resume over Tailscale.
- [ ] Verify owner/device binding, session expiry, revocation, replay rejection and rate limiting.
- [ ] Verify secure credential/MFA entry without chat/log/notification persistence.
- [ ] Verify that ordinary chat cannot submit orders or alter risk permissions.
- [ ] Verify offline behavior and recovery without interrupting local market-data collection.
- [ ] Complete physical Android launch, rendering and logcat checks.
- [ ] Run the end-to-end PAPER evidence chain and reconcile all displayed state with backend records.

Until these gates pass, remote conversational control is a product requirement and development target, not a certified production capability.
