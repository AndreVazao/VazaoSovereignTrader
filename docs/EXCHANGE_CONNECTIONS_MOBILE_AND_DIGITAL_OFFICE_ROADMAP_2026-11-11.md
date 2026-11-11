# Exchange connections, mobile cockpit and digital office — delivery plan

**Updated:** 2026-11-11  
**Baseline:** `main` at `5f73a6d13af42186a2ffade05511fc97d835a8e7`  
**Working branch:** `feat/exchange-readonly-mobile-office-foundation-2026-11-11`  
**Status:** architecture contract plus initial DPAPI vault foundation; no credential registration API, UI or live exchange probe is included.

## Product target

One sovereign PC runtime is the authority. The Windows cockpit, Android mobile cockpit and Digital Office are clients of that same runtime; none may host a second trading engine or independently infer financial state.

### 1. Exchange connections — first delivery track

Initial venues: Binance Spot and OKX Spot. Start with account identity/permission inspection and read-only balances. No order endpoints, trade permission, withdrawals, transfers or REAL controls in the first increment.

Credential UX:
- PC cockpit route: **Exchanges → Ligações e Contas**.
- Dedicated form served by the local authenticated PC API; credentials are submitted directly to loopback/local backend, never through chat, mobile, push, Vercel rendezvous or telemetry.
- Binance fields: API key and secret. OKX: API key, secret and passphrase.
- UI must clear secret inputs after submission and must not persist values in local/session storage, browser cache, URLs, analytics, logs or error messages.
- The server response returns only venue, connection status, permission classification, last verification time and a non-reversible credential fingerprint/label. Never echo key material.
- Require least privilege: read-only keys only. Reject credentials that report trade or withdrawal capabilities. Never request or accept withdrawal permission.
- Keep the feature disabled until encrypted-at-rest storage and redaction tests pass. On Windows use DPAPI CurrentUser protection with authenticated metadata and atomic writes. On unsupported platforms, fail closed; do not fall back to plaintext or ordinary environment/config files.
- Secrets must be decrypted only in process memory for the connector call, then references released. Do not serialize client objects or secret values.
- Private account reads require explicit owner action and authenticated scope. Rate-limit, timeout and audit outcomes without recording payloads containing private account data.
- Binance and OKX adapters must explicitly allow-list read-only methods. A generic CCXT authenticated client is not sufficient evidence of read-only behavior if order methods remain reachable.
- Test invalid keys, permission escalation, revoked keys, exchange timeout, malformed responses, storage corruption, DPAPI unavailable, log redaction and shutdown.

### 2. Android mobile cockpit

The existing `MOBILE_APP` is retained and evolved, not replaced. It connects to the same PC API using the existing owner/device pairing and private network path (Tailscale preferred). Exchange secrets never enter the APK.

First-class mobile views:
- Home: backend reachability, engine state/mode, data freshness and last update.
- Markets: venue/collector health, Radar and symbol watchlist.
- PAPER: positions, simulated fills, PnL and reconciliation evidence with explicit PAPER labels.
- Learning: vault health, cycles/records/events and evidence freshness; show unavailable/zero honestly.
- Alerts and human intervention: persistent pending tasks, approvals and manual OTP/CAPTCHA interaction without bypass.
- Chat: submit research/questions to the authenticated assistant gateway and render server-confirmed replies/task IDs.
- Exchanges: connection status and read-only balance summary only; no credential entry on mobile in this first phase.
- Settings: device pairing, endpoint selection, connection test, revocation and diagnostics.

Mobile safety and resilience:
- Device token remains in Android Keystore-backed encrypted storage; no plaintext fallback.
- Keep LAN/Tailscale failover for GET only. Never replay mutations after timeout.
- Show OFFLINE, STALE, UNKNOWN and BLOCKED distinctly; do not turn missing data into zeros or success.
- Bounded polling, backoff, cancellation on app pause, safe areas, portrait/landscape/tablet layout and low-memory profile.
- Closing or crashing the APK must not stop the PC engine.

### 3. Digital Office

The office is a visual shell over the same API and task/event contracts, not a simulation pretending to be live. Rooms map to real capability domains: CEO/coordination, Markets, Exchange Comparison, Radar, Research, Analysis, Central Memory, Risk, PAPER Lab, Recovery and Audit.

Delivery sequence:
1. Keep compact chat as the low-resource default and always-available fallback.
2. Connect office header and room cards to authenticated server snapshots with timestamps/freshness.
3. Connect the conversational surface to the assistant gateway; persist task IDs and render actual task status/evidence.
4. Render rooms from real events only; no invented agents, movement, balances, orders or profitability.
5. Bring the same office navigation to desktop and Android with responsive 2D/2.5D rendering.
6. Consider 3D only after performance, accessibility and device acceptance tests.

### API and security boundary

- PC_ENGINE remains authoritative for credentials, balances, risk, PAPER, future execution and audit.
- Local API binds to loopback by default. Remote access uses private authenticated networking; never expose port 8765 publicly.
- Device identity, owner identity, scopes and revocation are server-validated. Tailscale connectivity is not authorization.
- Exchange credential routes must use a dedicated owner-only scope, CSRF/origin protections appropriate to the local UI, strict payload size limits, no-store responses, bounded timeouts and audit metadata.
- Do not reuse the mobile device token as an exchange credential or grant exchange access to paired devices by default.
- Vercel/rendezvous may carry only minimal, short-lived endpoint discovery metadata; never credentials, balances, positions, orders or chat content.
- Any future mutation must define exact method, schema, scope, server guard, idempotency, audit and unknown-outcome reconciliation. Natural-language chat never authorizes financial actions.

## Incremental delivery and acceptance gates

### E1 — Secure read-only credential foundation (next implementation increment)
- [x] Inventory existing venue configuration, CCXT usage, route factory, scopes and test fixtures.
- [x] Add per-venue public market request/success/error/quality-rejection and persistence counters to the Radar.
- [x] Expose collector counters through authenticated `/paper-collector/resources` for PC/mobile observability.
- [ ] Run exact-head tests and validate metrics against live Windows runtime before treating collector health as proven.
- [ ] Add Windows DPAPI credential vault with fail-closed cross-platform behavior.
- [ ] Add explicit Binance/OKX read-only capability registry and permission verifier.
- [ ] Add authenticated owner-only register, verify, status and revoke routes; no secret echo.
- [ ] Add PC Cockpit form and redaction/no-store behavior.
- [x] Add unit/static contract tests for collector counters and Android Radar page wiring.
- [ ] Add contract, security, storage, timeout and negative-permission tests for credential registration and venue permission verification.
- [ ] Keep the feature disabled by default; do not ask the owner to create keys until the exact-head CI and security review pass.

### M1 — Mobile observability and conversation
- [ ] Map current mobile methods to existing API endpoints and scope requirements.
- [x] Add an Android Radar page showing authenticated public collector counters, per-venue successes/errors/rejections and last-observation freshness.
- [ ] Add typed, timestamped status models and stale/offline/unknown display across the remaining mobile views.
- [ ] Add bounded refresh and reconnect behavior without mutation replay.
- [ ] Connect chat to authenticated assistant gateway and durable research task IDs.
- [ ] Add PAPER, Radar, Learning Vault and alert views using real backend data.
- [ ] Verify APK build, emulator UI and physical Android launch/logcat separately.

### O1 — Digital Office integration
- [ ] Replace demo-only state with authenticated room snapshots.
- [ ] Render task progress and agent/department activity only from real backend events.
- [ ] Keep chat fallback, adaptive rendering and non-blocking observer behavior.
- [ ] Verify desktop and Android office parity against the same API contracts.

### Release gates
- [ ] Exact-head Python, Android APK, Android emulator, Windows EXE/installer and PAPER smoke workflows pass where applicable.
- [ ] Security tests prove no plaintext credential persistence, no secret logging and no trade/withdrawal capability.
- [ ] Android tests distinguish CI build from emulator and physical-device evidence.
- [ ] End-to-end private-network test proves pairing, revocation, chat/task recovery and stale/offline behavior.
- [ ] No merge or installation based solely on a green build; inspect artifacts and exact SHA.

## Explicit non-goals for this phase

No live order placement/cancellation, no REAL activation, no transfers/withdrawals, no public API exposure, no paid mandatory cloud service, no credential collection in chat/mobile, no second engine and no claims of profitability.
