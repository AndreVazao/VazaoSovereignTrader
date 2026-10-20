# Headless Sovereign Trader, PC cockpit, desktop office and Android client

**Status:** target architecture and staged implementation plan. This document does not claim that remote access or the visual office is already integrated.

## Principle

Sovereign Trader is a headless backend: it runs as a background service on a normal PC or dedicated server without requiring an open window. It remains the single authority for market data, exchange connectors, strategy state, risk, orders, balances, recovery, and audit records.

The cockpit, desktop virtual office and Android APK are separate installable clients. They show backend state and send authenticated, authorized requests. They must not run a second trading engine, maintain their own authoritative positions, or contain exchange API secrets.

## Installable components

### 1. Sovereign Trader Backend
- Runs as a Windows background service/process independently of the logged-in desktop UI; dedicated-server deployment can follow the same contract.
- Owns exchange credentials/connectors, market and research workers, risk authorization, execution, persistence, recovery and audit history.
- Exposes a versioned API for health, status, events, diagnostics, approved commands and human-intervention requests.
- Binds to loopback by default. Remote access must be explicitly configured through a private network/VPN or secure gateway; never expose the API directly to the public Internet.
- Enforces authentication, device pairing/revocation, command permissions, server-side risk checks, rate limits, and auditable operator actions.

### 2. Local PC cockpit
- A lightweight control surface installed on the backend PC for connection/service status, PAPER/REAL mode, readiness, alerts, logs, start/pause/resume/stop requests and pending human intervention.
- Closing the cockpit window must not stop the configured backend service.
- UI controls never bypass server-side authorization or risk checks.

### 3. Optional desktop Virtual Office
- A separately installable application that can connect to a local backend or a backend running on another PC/server.
- Provides **Chat/compact cockpit** and **Virtual Office** modes. Switching mode changes presentation only, not permissions or trading logic.
- Rooms represent real backend capabilities: exchanges, market data/order book, technical research, cross-venue timing, news/event research, fees/liquidity, risk/portfolio, PAPER lab, recovery and audit.
- Start with responsive 2D/2.5D. Optional 3D is a later layer, only after data contracts and performance are proven.
- Quality profiles: Lite (static, minimal animation), Standard (2D/2.5D), Advanced (optional 3D), with automatic hardware adaptation, manual override and chat-only fallback.
- Every status, avatar, carrier or movement that claims to represent live activity must be backed by actual backend events. Never fabricate transfers, agents, profit or exchange status.
- A rendering failure must not stop or impair the backend.

### 4. Optional Android APK
- A remote client to the same backend, not a mobile trading engine.
- Supports compact chat, status/readiness, alerts, permitted commands, logs and human approval requests.
- Exchange keys never enter the APK. Pair devices securely, support revocation, avoid plaintext token persistence, and use platform-secure storage for device credentials.
- Layout must respect Android status-bar/safe areas and short screens, keep controls reachable and allow scrolling. Prefer compact/chat mode over a desktop-style 3D office.
- Clearly show offline/stale data; do not report a command as successful until the server confirms it.

## Remote command lifecycle
1. Backend starts and reports version, health, mode and data freshness.
2. Operator explicitly pairs a client; access can be revoked per device.
3. Client connects over a private network, authenticates and negotiates API version/capabilities.
4. Client reads state/events and sends a validated command with request/idempotency identity where appropriate.
5. Backend authenticates, authorizes, checks current state/mode and risk, executes or rejects, and records an audit event.
6. Client displays the server's result and timestamp. A timeout means “outcome unknown until reconciled”, not success or failure.

The backend remains authoritative across simultaneous clients. User-specific tokens, preferences, operational data, balances and positions stay isolated. Sharing validated research/learning across installations must be a separate, explicit export/import or governed knowledge-sync feature; it must never share account credentials or private trading state by default.

## Human intervention
The backend creates a persistent, expiring request when a human must complete a login, manual 2FA/OTP, CAPTCHA or confirmation. Connected clients notify the operator and present the request, while the browser/session remains on the backend PC. Challenges are completed manually; there is no bypass. Sensitive input must not enter ordinary logs.

## API contract
Audit the existing routes before adding new ones. The contract should cover health/version/status/readiness, event stream or polling with reconnect IDs, authorized commands, exchanges, portfolio/risk, research/PAPER, human interventions, audit and diagnostics. Add timeouts, retry/backoff, stale-data indicators, cancellation and explicit handling of unknown command outcomes. Avoid duplicating existing endpoints blindly.

## Delivery order
1. Reproduce and diagnose the current Android startup crash using the APK build output and Android logcat; a layout fix alone does not prove the crash is fixed.
2. Stabilize backend service lifecycle and document the existing API contract without changing the trading engine's authority.
3. Implement secure device pairing, revocation and scoped permissions; test remote access over a private network.
4. Keep the local cockpit lightweight and independent from backend process lifecycle.
5. Build the desktop client in chat/compact mode, connecting to a local or remote backend.
6. Connect office rooms to real API state/events; keep 2D/2.5D optional and chat-only fallback always available.
7. Add adaptive visual profiles and optional 3D only after functional and performance tests.
8. Validate client disconnects, backend restart, stale data, duplicate commands, revoked devices, pending human intervention and unknown execution outcomes before any REAL use.

## Acceptance criteria
- Backend runs headlessly with no cockpit, office or phone open.
- Closing/crashing a client does not stop or duplicate the engine.
- A separately installed desktop client connects to another PC's backend through a configured private network.
- Desktop and Android clients show the same server-authoritative state and data freshness.
- Privileged commands are authenticated, authorized, validated server-side and audited.
- Chat-only mode remains usable on low-power devices and during rendering failure.
- No visual animation claims to be a real transfer/trade unless backed by a real event.
- APK build, install, startup, pairing, reconnect and device layout are tested on a real Android device.
- PAPER safety validation remains mandatory; the office is not a REAL-readiness certificate.
