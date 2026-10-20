# Sovereign Trader: backend, cockpit clients and virtual office

**Status:** target architecture / implementation plan. This document does not claim that remote access, authentication, or the visual office are already complete.

## 1. Core rule

Sovereign Trader is a headless backend. It runs as a background service on the user's primary PC or a dedicated server and does not require a desktop window to keep its engine running. The backend is the single authority for market data, strategy state, risk checks, orders, balances, recovery, audit history and exchange credentials.

The cockpit, desktop office and Android app are separate clients. They present backend state and send authenticated, authorized requests. They must not start a second trading engine, independently decide the authoritative position, or store exchange API secrets.

## 2. Installable components

### A. Sovereign Trader Backend (server)

- Windows service / background process first; dedicated-server deployment can follow the same service contract.
- Starts independently of a logged-in desktop session and can recover after restart according to explicit recovery policy.
- Owns exchange connectors, market/research workers, risk authorization, execution, persistent state and audit logs.
- Exposes a versioned API on a private network, with health/readiness, events, human-intervention requests and command endpoints.
- Binds to loopback by default. Remote use must be explicitly configured through a private overlay network or secure gateway; do not expose the API directly to the public Internet.
- Requires authentication, per-device pairing/revocation, authorization by command class, rate limits, replay protection where appropriate, and auditable operator actions.
- Treats a disconnected client as a presentation/connectivity issue, never as permission to weaken risk controls.

### B. Local PC cockpit (small, always-available control surface)

- A lightweight interface installed alongside the backend, for basic local monitoring and control.
- Provides connection/service status, start/pause/resume/stop requests, current mode (PAPER/REAL), risk/readiness summaries, alerts, logs and pending human interventions.
- It is a control surface, not the engine itself; closing the window must not accidentally stop a configured background service.
- High-impact operations require server-side checks and explicit confirmation. UI visibility never bypasses backend authorization.

### C. Desktop Virtual Office (optional, independent install)

- A separately installable desktop client that connects to a selected Sovereign Trader backend, including one hosted on another PC or dedicated server.
- Offers two presentation modes: **Chat / compact cockpit** and **Virtual Office**. Switching modes changes only the interface, not trading logic or permissions.
- The visual office is an observability and navigation layer. Rooms/departments open real backend views: exchange connector status, market data, research, technical lab, cross-venue timing, fees/liquidity, risk/portfolio, PAPER lab, recovery and audit.
- An office room, avatar, carrier or animation may only represent a real entity/event when the backend supplies corresponding evidence. Never fabricate workers, transfers, positions, profit, or live status for visual effect.
- Start with a fast 2D/2.5D layout. Add optional 3D only after API contracts, status mapping and performance measurement are stable.
- Quality profiles: Lite (static/low-motion), Standard (2D/2.5D), Advanced (optional 3D). Automatically adapt rendering to available CPU/GPU/RAM, allow manual override, and fall back to chat-only without reducing engine or risk processing.
- The visual office must remain optional: its crash or shutdown cannot stop the backend.

### D. Android APK (optional, independent install)

- A remote client for the same backend, not a mobile trading engine.
- Supports compact chat/cockpit, health/readiness, alerts, permitted commands, logs and human approval flows.
- Uses secure device pairing and revocation; exchange API keys never enter the APK. Do not persist owner tokens in plaintext. Secrets and session tokens must follow platform-secure storage and short-lived/revocable credential policy.
- Must work on small screens with safe-area/status-bar awareness, scrollable content and reachable controls. It should fall back to chat/compact mode rather than attempt to render a desktop office.
- The client must clearly show stale/offline data and must never imply a command succeeded until the backend confirms it.

## 3. Connection and authority model

1. Backend starts and reports health, version, mode and data freshness.
2. An operator pairs a desktop or phone client from the server side; access is revocable per device.
3. The client establishes an authenticated connection over a private network (for example, a private overlay VPN) and negotiates API version/capabilities.
4. Client reads status/events and sends a command with an idempotency/request identifier where relevant.
5. Backend authenticates, authorizes, validates current mode, checks risk and state, executes or rejects the request, and records the result in the audit trail.
6. Client displays the server's result and timestamp; timeout means “unknown until reconciled”, not “failed” or “successful”.

The backend remains authoritative if multiple clients connect simultaneously. User-specific accounts, tokens, preferences and operational data remain isolated. Sharing learned research/validated knowledge between installations, if later implemented, must be an explicit export/import or governed knowledge-sync feature and must not share private account credentials, positions, or identity data.

## 4. Human intervention

When the backend requires login, manual 2FA/OTP, CAPTCHA, or another human step, it creates a persistent intervention request with a clear purpose, expiry, target service, and status. Connected clients can notify the operator and present the request. The actual browser/session and sensitive execution remain on the server/PC. CAPTCHA and other challenges are completed manually; there is no bypass. Sensitive input must not be written to ordinary logs.

## 5. API and reliability contract

Build and version a narrow API before connecting richer clients. Initial resource families:

- `/health`, `/version`, `/status`, `/readiness`
- `/events` (stream or poll, with event IDs and reconnect handling)
- `/commands` (validated, authorized, auditable requests)
- `/portfolio`, `/risk`, `/exchanges`, `/research`, `/paper`
- `/human-interventions` (list, acknowledge, submit allowed response, expire)
- `/audit` and diagnostics, with sensitive fields redacted

Exact endpoint names should follow the existing API after a compatibility audit; do not duplicate routes blindly. Every client needs timeouts, retry/backoff, stale-data indicators, cancellation, and safe handling of unknown command outcomes.

## 6. Implementation sequence

1. Stabilize the current Android app and reproduce/diagnose its startup crash using build output and Android logcat. UI layout fixes alone do not prove the crash fixed.
2. Define the backend service lifecycle and API contract, preserving the existing engine as the sole execution authority.
3. Add authenticated device pairing, per-device revocation and explicit permission scopes; test remote access on a private network.
4. Keep the local PC cockpit small and reliable, independent from engine process lifecycle.
5. Deliver the desktop client in chat/compact mode first, connecting to a local or remote backend.
6. Bind office rooms to real API data and events; begin in 2D/2.5D with truthful states and a chat-only fallback.
7. Add adaptive visual profiles and optional 3D only after functional and performance tests.
8. Validate client disconnection, backend restart, stale data, duplicate commands, revoked devices, pending human interventions, and unknown execution outcomes before any REAL use.

## 7. Acceptance criteria

- Backend can run headlessly with no cockpit or office window open.
- Closing or crashing any client does not stop or duplicate the engine.
- A separately installed desktop client can connect to a backend on another PC through a configured private network.
- Android and desktop clients show the same server-authoritative state and report data freshness.
- Every privileged command is authenticated, authorized, validated server-side and auditable.
- Chat-only mode remains available on low-power devices and during visual-rendering failure.
- No UI animation is presented as a real exchange transfer or trading result unless backed by a real event.
- APK build, install, startup, pairing, reconnect and device-specific layout are tested on an actual Android device; unit tests alone are insufficient.
- PAPER validation and safety controls remain mandatory; the office is never a REAL-readiness certificate.
