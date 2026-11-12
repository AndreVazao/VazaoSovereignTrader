# VST — Universal Platform Integration & Android Virtualization Architecture

**Date:** 2026-11-12
**Baseline:** 09b803a2ce0bba10de895b800fd8950a60e739a1
**Status:** architecture contract; no cloud Android provider provisioned and no external account connected.

## Product requirement

VST must not be hard-coded around a short list of exchanges. Binance and OKX are only the first financial connectors used to prove a strict capability boundary. The long-term platform must integrate with suitable exchanges, brokers, fintech services, wallets, banking/portfolio applications, Android applications, web services and desktop applications through replaceable adapters.

Examples include U-Hodler and other user-selected services. Naming a service does not imply that an official API exists, access is permitted, or a connector is already implemented. Each integration begins with a capability and access-method assessment.

## 1. Universal connector architecture

Introduce a platform-neutral connector registry. Each connector declares:
- Stable provider ID, display name, category, supported regions and documentation references.
- Access method: official API, OAuth, supported SDK, export/import, browser session, Android UI automation or manual-only.
- Authentication model and secret references, never raw secret values in registry records.
- Explicit capability manifest, permission requirements, data classes, rate limits, timeouts and provider terms/constraints.
- Supported operations and schemas, freshness semantics, pagination, idempotency and error taxonomy.
- Health state: AVAILABLE, DEGRADED, AUTH_REQUIRED, RATE_LIMITED, UNSUPPORTED, REVOKED, BLOCKED, OFFLINE or UNKNOWN.
- Evidence: adapter version, contract-test version, last successful validation and source timestamp.

Connector categories are open-ended: exchange, broker, fintech, banking, wallet, payments, portfolio, market_data, android_app, web_app, desktop_app, cloud_service and future categories. Categories are descriptive, not permission grants.

### Connector selection order
1. Official documented API with least-privilege scopes.
2. Official OAuth/SDK or approved partner interface.
3. User-authorized export/import or documented integration endpoint.
4. Browser/desktop/Android UI automation only when no suitable supported interface exists and provider terms and user authorization allow it.
5. Manual workflow when automation is prohibited, unreliable or requires a human decision.

Never scrape or reverse-engineer private endpoints as a default integration strategy. Do not bypass MFA, CAPTCHA, device binding, regional controls, rate limits or provider safeguards.

## 2. Capability and permission model

No adapter receives generic unrestricted network or account authority. Every operation is checked server-side against owner, connector, account, device, scope and current policy.

Initial capability families:
- public_market_data.read
- account_identity.read
- account_permissions.read
- balances.read
- transactions.read
- positions.read
- portfolio.read
- statements.read
- orders.read
- orders.simulate
- orders.create (disabled)
- orders.cancel (disabled)
- funds.transfer (disabled)
- funds.withdraw (disabled)
- profile.manage (disabled)
- device.ui.observe
- device.ui.interact
- human.approval.request

Unknown capabilities and operations fail closed. A read-only connector must not expose mutation methods through a generic CCXT/browser/client object. Provider permission responses are normalized into typed, evidence-backed snapshots; missing, stale, malformed or ambiguous snapshots become BLOCKED or UNKNOWN, never implicitly read-only.

Financial mutations, deposits, withdrawals, transfers, order placement/cancellation and permission changes remain disabled. A future proposal requires separate risk design, explicit owner approval, exact operation allow-list, idempotency, audit, limit checks and unknown-outcome reconciliation. Chat text alone never authorizes a financial action.

## 3. Android virtualization service

VST must support Android applications the owner needs to inspect or operate, including apps without a usable API, through a pluggable Android virtualization provider.

Target architecture:
- Android Session Orchestrator: creates, assigns, health-checks, pauses and destroys virtual Android sessions.
- Provider adapters: support a self-hosted Android emulator farm and optional third-party/cloud Android device providers. Provider choice is configuration, not a hard dependency.
- Device profiles: configurable Android version, ABI, screen size, density, locale, timezone, network policy and resource budget.
- Secure session gateway: authenticated remote display/control stream to the owner cockpit; short-lived session tokens; no public unauthenticated ADB/debugging ports.
- App catalogue: owner-approved package inventory, version, install source, requested permissions and app-specific automation contract.
- Automation workers: isolated per session; bounded actions, screenshots, accessibility/UI hierarchy where available, OCR fallback, explicit waits and post-action state verification.
- Evidence store: timestamped screenshots, action summaries, app/version, session ID and outcome. Redact sensitive screen regions where possible; never store passwords, OTPs, recovery phrases or full payment details.
- Human handoff: pause and request owner interaction for MFA, OTP, CAPTCHA, biometric prompts, consent, payment confirmation, account recovery or ambiguous security screens. Never bypass or auto-solve these gates.

### Local versus cloud execution
- Prefer a local emulator when the PC has sufficient resources and the app permits it.
- Use cloud virtualization when the PC is resource-constrained, the owner is away, multiple apps/devices are needed, or persistent remote sessions are required.
- Allow multiple providers behind one interface; do not bind VST to one vendor or make a paid provider mandatory.
- Keep a self-hosted option for sovereignty and cost control.
- Cloud sessions use encrypted transport, isolated tenant/device workspaces, short-lived credentials, least-privilege egress, retention limits and explicit region/data-residency configuration.
- Never put exchange credentials or app passwords into emulator images, snapshots, recordings, automation prompts or cloud logs. Inject short-lived secrets only through a reviewed secure broker; otherwise require owner entry directly in the authenticated session.
- Treat snapshots as sensitive data. Disable persistent snapshots by default; if enabled, encrypt and expire them under owner policy.
- No ADB over public internet. Use private authenticated tunnels or provider-native secure streaming and device-control channels.

### Application interaction policy
For each Android app, define a reviewed workflow contract. UI automation is less reliable than APIs and must expose confidence, observed screen state and recovery outcome. Destructive or financial actions require human approval; automation stops on unexpected screens, changed terms, new permissions, account warnings or uncertain state.

Supported examples after individual review: read portfolio/balance summaries, inspect transactions, download statements, monitor account status, collect public information and prepare a user-reviewed report. This grants no authority to transfer funds, trade, borrow, repay, change security settings or accept contractual terms.

## 4. Security, privacy and sovereignty
- PC_ENGINE remains the policy authority; cloud Android is an execution surface, never an independent financial brain.
- Bind every session and connector to owner, organization, installation, device and task identities. Never trust client-supplied IDs alone.
- Separate connector secrets, Android app secrets, device tokens and VST local API tokens.
- Enforce encrypted secret storage and redaction; never log credentials, OTPs, recovery codes, private account payloads or full screen recordings by default.
- Enforce origin/CSRF protections, authenticated scopes, request size limits, timeouts, rate limits and explicit revocation.
- Default to read-only and observation. UI interaction is a separate capability granted per app/session.
- Keep audit evidence tamper-evident without copying sensitive payloads.
- Cross-organization isolation applies to connector metadata, credentials, device sessions, screenshots, recordings, task history and Learning Vault data.
- Cloud discovery/rendezvous exchanges only minimal short-lived connection metadata, never secrets or financial payloads.

## 5. Delivery phases

### P0 — architecture and inventory
- [x] Record universal connector and Android virtualization requirements.
- [ ] Inventory current connector/client construction points and existing Android app automation.
- [ ] Define typed connector manifest and capability registry schemas.
- [ ] Build provider-neutral interface contracts and fake adapters.

### P1 — safe read-only connector runtime
- [x] Establish initial fail-closed Binance/OKX read-only policy foundation.
- [ ] Move venue-specific policies behind the universal capability registry.
- [ ] Wrap authenticated clients so callers cannot bypass capability checks.
- [ ] Add provider-specific permission probes and owner-only credential lifecycle API.
- [ ] Add contract tests for unsupported providers, stale permissions, secret redaction, revocation and timeout.
- [ ] Add connector health/freshness and per-provider observability.

### P2 — Android virtualization proof
- [ ] Compare self-hosted emulator and cloud Android providers on security, price, geography, session persistence, streaming latency, automation access and exportability.
- [ ] Implement provider-neutral session orchestrator and a local emulator adapter first.
- [ ] Add one cloud provider adapter behind the same interface; keep deployment opt-in and cost-capped.
- [ ] Demonstrate a read-only workflow in one owner-selected Android app, with human handoff for authentication/security gates.
- [ ] Test session isolation, expiry, revocation, evidence redaction, unexpected-screen stop and recovery.
- [ ] No production app credentials until secret broker and threat model are approved.

### P3 — multi-platform operator
- [ ] Unified platform catalogue for Android, web, desktop and API connectors.
- [ ] Task planner chooses an approved connector based on capabilities, reliability, cost and user policy.
- [ ] One audit/task timeline across connectors and virtual Android sessions.
- [ ] Cockpit shows live session, human handoff, connector health and evidence; chat/mobile never stores provider secrets.
- [ ] Offline/manual fallback when a provider is unavailable.

## 6. Acceptance gates
- Exact-head Python tests, PAPER smoke and applicable Windows EXE/installer tests pass.
- Capability tests prove unknown operations and permissions fail closed.
- No secret appears in logs, artifacts, screenshots, telemetry or error responses.
- Cloud Android tenant/session isolation and secure remote-control tests pass before any real app account is used.
- App workflow tests prove stop-on-uncertainty and human handoff.
- Cost controls include per-session budgets, maximum runtime, idle shutdown and owner-visible usage.
- No merge based only on documentation or build success when runtime behavior changed; inspect exact-head evidence.

## Explicit non-goals
No exchange lock-in; no mandatory cloud vendor; no public ADB; no MFA/CAPTCHA bypass; no unattended financial mutation; no secret entry in ChatGPT; no REAL trading activation; no claims that an app is integrated before its adapter and acceptance tests exist.