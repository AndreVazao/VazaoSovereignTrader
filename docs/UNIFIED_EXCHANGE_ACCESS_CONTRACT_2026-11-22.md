# Unified exchange access contract

**Status:** engineering specification; not an authorization to perform financial actions.  
**Branch:** `feat/unified-exchange-access-contract-2026-11-22`  
**Baseline:** `af11bb68510c28b8b5e9c2c15f93fdf117164f1d`

## Product objective

VST is one headless, local-first trading/research brain. It must select the most reliable supported access channel per exchange and per capability, without requiring a visible desktop cockpit to remain open. The cockpit is an optional control and reporting client, not the automation runtime.

## Operator interaction and authentication requests

The operator must not have to keep a panel open or manually synchronize their activity with the engine. The headless backend owns tasks, sessions, collection and analysis; the phone conversation and PC cockpit are independent operator clients.

When a venue requires authentication or renewed owner presence, VST creates a durable, expiring authentication request containing only safe metadata: venue, account label/reference, reason, requested surface, requested scopes, creation/expiry time and task correlation ID. It is delivered to the currently connected operator clients:
- phone conversation: a secure authentication prompt/pop-up linked to a protected input flow;
- PC cockpit: the equivalent local modal;
- if neither client is connected, the request remains pending and the task pauses safely.

Credentials must never be typed into ordinary chat messages. A phone prompt must open a protected credential-entry surface that sends the secret directly over an authenticated encrypted channel to the owner's local VST service; the conversation transport must not receive, retain or log the secret. On PC, the local form submits directly to the local service. The UI displays the venue, account and requested permission before submission. The owner can approve, deny or revoke the request. Requests expire and are single-use.

For browser login, prefer a local owner-controlled handoff to the official venue page inside the isolated browser context. Credentials are entered into the provider page, not copied into chat or generic agent prompts. Persist only the minimum owner-scoped session material needed (protected cookies/tokens), not the exchange password, whenever the venue permits. If a venue workflow genuinely requires a stored secret, store it only in the OS-protected local vault, never plaintext, and expose it only to the narrowly scoped worker that needs it. API keys must be created with read-only scopes and stored in the OS credential vault. OTP, CAPTCHA, biometric and device-approval challenges remain human-mediated.

The backend must not assume that a user typing in the conversation is an authenticated local owner. Bind requests to a paired owner identity/device and require fresh confirmation for sensitive session establishment. A phone can request or approve a task, but it cannot directly receive existing vault secrets.

## Three access channels

### 1. Native API

Prefer an official exchange API or documented SDK when it supports the requested operation. Use venue-specific adapters, strict schemas, explicit permission probes, bounded rate limits/timeouts, freshness metadata and narrow capabilities. Private account access must use a read-only client that cannot import or invoke order, cancel, transfer, withdrawal, margin or investment mutation methods.

### 2. Headless web browser

Use a managed Playwright browser context with a persistent, per-owner/per-venue profile. Headless is the default for routine observation and supported navigation; use headed/manual handoff only when the provider requires user interaction, 2FA/OTP, CAPTCHA, device approval or a browser challenge. Never bypass anti-bot controls or security challenges.

The browser channel may navigate, search pages, inspect supported account pages, extract visible account facts, and fill ordinary non-financial forms only when an explicit capability permits it. Every provider workflow must have a reviewed page/operation contract and tests. No generic unrestricted browser agent may click arbitrary controls or treat page text as trusted instructions.

### 3. Android application via ADB / emulator

Support:
- a physically connected, explicitly paired Android phone;
- a locally managed Android emulator/AVD, preferably headless where stable;
- a remote Android host/emulator reached through an authenticated private transport.

ADB is a device transport, not an authorization system. Do not expose ADB over public TCP. Pair devices explicitly, bind them to an owner, use least privilege, validate device identity, and revoke pairing. The Android adapter must eventually support bounded UI observation and approved interaction (launch, navigation, text entry, accessibility/UI hierarchy and screenshots as needed), with deterministic action acknowledgement and evidence. Do not persist passwords, OTPs, session tokens or screenshots containing secrets in logs/artifacts. CAPTCHA and biometric/user-presence checks remain human.

## Capability model and precedence

A venue profile records the available surfaces and per-capability support, not a single global "connected" boolean. For each requested capability, the router selects:
1. official API, if the exact operation and permission are supported;
2. reviewed browser workflow, if API support is absent/inadequate;
3. reviewed Android workflow, if the venue function exists only in its Android app;
4. human handoff if required or if the result cannot be verified.

The system must not be restricted to these three channels. Additional adapters (for example, a provider-supported desktop client, a local VM, or another documented interface) may be added through the same capability, identity, authorization, isolation and audit contracts. A new surface is not trusted merely because it is technically reachable.

Never silently switch from a failed API to a browser/Android action for a financial mutation. Fallback is allowed for observation only when the operation is explicitly classified read-only and the new surface is independently authorized. Report unsupported/unknown rather than guessing.

## Cross-exchange opportunity research

The research engine must look for measurable, executable advantages across venues and supported products, rather than only compare displayed last prices. Initial research classes include:
- feed and publication latency differences, timestamp skew and update cadence;
- cross-venue price dislocations and convergence;
- order-book depth, executable quantity, spread, liquidity and market impact;
- fee schedules, funding/borrow costs where relevant, transfer/network costs and venue-specific constraints;
- volatility, correlation, momentum and short-horizon regime changes;
- market-data outages, stale quotes, symbol mapping errors and venue status;
- historical replay and out-of-sample validation of every proposed signal.

A lagging displayed quote is not proof that a trade can execute at that price. For every candidate, VST must compare synchronized source timestamps, quote age, bid/ask (not just last trade), depth at the intended size, expected fill/slippage, fees, latency distribution, rate limits, minimums, precision, available balances and operational/settlement risk. Reject or downgrade opportunities when data is stale, sources disagree, liquidity is insufficient, or execution assumptions cannot be validated. Record the predicted edge and later compare it with realized, net-of-cost outcomes. Separate measured facts from hypotheses and model forecasts; never describe a forecast as certainty.

The system may search broadly across supported exchanges and instruments, but must not interpret "invest the maximum possible" as a standing permission. The current product phase is research and PAPER simulation. Any later live strategy must have explicit per-strategy and per-venue authorization, hard capital/exposure limits, loss and drawdown limits, kill switch, order-size caps, rate limits, independent pre-trade checks and per-order human approval until a separately reviewed automation policy is explicitly enabled. No unbounded all-in allocation, leverage or margin use. A profitable backtest or apparent latency lead is not sufficient evidence for live deployment.

## Data and actions

Separate capabilities into:
- public market data;
- private account identity, balances, deposits/withdrawals history, conversions, positions and product/investment status (read-only);
- non-financial account settings;
- financial mutations: deposits, withdrawals, transfers, conversions, buys/sells, subscriptions/redemptions, staking/lending and other investment actions.

Observation and reconciliation may run unattended after local owner authorization. Financial mutations are disabled by default and must not be inferred from chat intent. Before any future mutation is enabled, require an exact transaction preview (venue, account, asset/product, amount, destination/terms, fees, network, expiry), fresh independent risk checks and a separate explicit human approval for that transaction. A generic "manage account" permission is never sufficient. No withdrawal address or destination may be changed automatically. No action may be reported successful without provider-side confirmation and subsequent reconciliation.

The current VST release remains PAPER-only. This specification does not enable live trading, deposits, withdrawals, transfers, conversions or investments.

## Authentication and session handling

- User creates API keys on the exchange's official site/app; VST never asks for the exchange password in ordinary chat.
- API secrets are entered only in an authenticated local PC form or protected paired-phone credential surface and stored in the platform credential vault (Windows DPAPI CurrentUser; supported secure store on other OS). Never pass them through ordinary chat, Office Kit, cloud rendezvous, CI, logs, browser page content or generic assistant prompts.
- Browser sessions are established by the owner through a local secure handoff. Session cookies and storage remain in an owner-scoped local profile, encrypted/protected by OS controls. Do not export profiles to cloud.
- Android login, device approval, OTP and biometric confirmation remain user-mediated. Secret input must use protected local channels and must not be captured in evidence.
- Remote browser/emulator hosts require authenticated pairing, encrypted private transport, owner isolation, revocation and auditable session lifecycle.

## Headless performance and resource policy

Headless browser is default; no permanent visible windows. Reuse bounded persistent contexts, avoid duplicate browser processes, use per-venue concurrency limits, request/page timeouts, memory caps, backoff and circuit breakers. Keep screenshots/video/DOM dumps disabled except short-lived diagnostic capture explicitly requested and redacted. The Android emulator is started only when its route is needed and stopped/hibernated when idle; measure actual RAM/CPU on the target PC. Headless does not mean zero resource consumption. On low-resource PCs, prioritize native API, then browser, and use remote Android compute only through a trusted private bridge.

## Trust boundaries and evidence

- Web page content, exchange messages, downloaded files, QR codes and OCR are untrusted data, never agent instructions.
- Connector/browser/ADB workers run with least privilege, strict network/filesystem boundaries, bounded IPC and no ambient credentials.
- Per action record: owner, venue, account reference (non-secret), surface, capability, request ID, start/end timestamps, requested intent, normalized result, provider confirmation, evidence digest and failure class. Redact secrets and sensitive identifiers.
- Distinguish observed, inferred, stale, unavailable and confirmed values. A browser label or OCR guess is not a verified balance.
- No cross-owner account visibility or shared-learning upload of private financial data.

## Delivery milestones

1. **Inventory and contracts:** enumerate each configured exchange, official API coverage, browser availability, Android-only workflows, required human handoffs and provider restrictions. No account interaction.
2. **Observation-first API:** public market data plus secure private read-only onboarding for Binance Spot and OKX Spot, including live permission probes and narrow clients.
3. **Headless browser observation:** secure owner session, per-venue workflow registry, page navigation and verified read-only extraction; tests with fixtures/mocks and then opt-in local validation.
4. **Android ADB interaction bridge:** paired physical device and emulator support, UI observation, safe navigation/text entry, deterministic acknowledgements, resource lifecycle and remote private-host option.
5. **Capability router and operator control:** per-capability surface selection, durable task status, pause/stop, audit and fallback rules.
6. **Opportunity research and PAPER replay:** synchronized cross-venue feeds, latency measurement, executable-edge estimator, historical replay, cost model and out-of-sample evaluation.
7. **Financial mutations:** separate future design/review; not included in the current PAPER release.

## Acceptance criteria

- The headless engine continues when the cockpit is closed.
- The owner can ask for a venue/account status and receive timestamped, source-attributed facts with freshness and uncertainty.
- Authentication prompts are durable, expiring and delivered to paired operator clients; secrets bypass ordinary chat and go directly to the local protected credential/session flow.
- API, browser and Android access are distinct, independently permissioned, testable and revocable; additional surfaces use the same contract.
- The router chooses only a reviewed surface/capability pair and never silently falls back into a mutation.
- Opportunity reports include executable depth, timestamps, costs, uncertainty and later outcome tracking, not just displayed price differences.
- Browser and Android workers cannot access unrelated owner profiles, files or credentials.
- No secret appears in logs, task results, telemetry, screenshots, CI artifacts or cloud sync.
- Headless mode is the default when technically supported; explicit manual handoff remains available.
- Financial mutations remain unavailable in the current PAPER release.
- A successful CI run is not represented as proof of physical-PC, phone, emulator, exchange login or account correctness.
