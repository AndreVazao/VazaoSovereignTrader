# VST install readiness and data acquisition gates

**Audit date:** 2026-11-22  
**Audited main:** `ac88989caeff86198339de38e241b3e52560e791`  
**Purpose:** distinguish implemented capabilities from the remaining work required for a safe, useful first PC installation. This document is an audit, not a release declaration.

## Executive decision

The VST has a substantial PAPER research foundation and can collect public market data without exchange credentials. It is **not yet certified as a complete PC brain**, and private exchange-account ingestion is not ready to be enabled for the owner.

Keep the runtime PAPER-only. The first account-data milestone is read-only account identity, permission verification and balances, beginning with Binance Spot and OKX Spot. No order, cancel, transfer, withdrawal, margin, futures or REAL capability is part of that milestone.

## Verified implementation on the audited main

- Public CCXT market-data adapters support bounded ticker, OHLCV and order-book reads.
- Radar polling and public WebSocket collectors exist; the Radar is observational-only.
- OHLCV validation rejects missing/non-finite values, invalid OHLC relationships, duplicate/non-increasing timestamps and configured gaps/age violations.
- PAPER research, state-signature learning, outcome records, evidence ledger, readiness history/trend and scorecard components exist.
- The local API has an authenticated assistant gateway at `POST /assistant/message`; its implemented intent surface is deterministic and bounded, not a general-purpose agent executor.
- A Windows DPAPI CurrentUser credential vault exists for Binance and OKX. Unsupported platforms fail closed.
- A pure Binance/OKX read-only capability policy exists and permits only `fetch_balance` and `fetch_accounts`; permission evaluation blocks incomplete, malformed or unsafe permission snapshots.
- A Linux Bubblewrap command builder supports explicit runtime manifests. A minimal packaged CPython closure and real Bubblewrap CI probes exist.
- Windows installer CI has exercised install/upgrade/launch/health/uninstall and Learning Vault preservation in disposable CI.

## Gaps that block the requested operating model

### A. Private exchange-account ingestion — not ready

- The DPAPI vault is not yet connected to an owner-only credential registration/verification API or a PC secure-entry form.
- The existing capital venue discovery path reads environment variables and can construct the broad `CcxtExchangeClient`; it does not consume the DPAPI vault or the Binance/OKX capability policy.
- The permission policy is a pure evaluator. Venue-specific live permission probes and strict normalization for Binance and OKX are not wired.
- The generic exchange client exposes trading methods. It must not be reused as an account-read adapter without a narrow wrapper that makes non-read operations unreachable to the account-ingestion path.
- Current discovery configuration lists six venues, but the secure vault and permission policy support only Binance and OKX. Do not imply the other four are ready.
- No private account credentials have been requested, loaded, or tested as part of this audit.

**Acceptance:** secure owner-only local registration; DPAPI encryption; no secret echo/logging; provider-specific permission probe; strict read-only method wrapper; only verified read permission and explicitly disabled trade/withdraw/transfer permissions accepted; bounded requests; sanitized audit; revocation; corrupt-vault and permission-escalation tests. Start with Binance Spot and OKX Spot only.

### B. Connector worker isolation — not production-integrated

- The manifest-backed Bubblewrap builder and packaged Python runtime are groundwork.
- The trusted production parent does not yet launch the worker through the strict manifest-backed command before connector code executes.
- The registry still has an in-process adapter path. The current worker/resource controls do not turn arbitrary in-process adapters into sandboxed code.
- Linux worker networking is deny-all. Provider-specific HTTPS egress does not exist.
- Windows Job Objects provide process/resource limits, not filesystem or network isolation.

**Acceptance:** production supervisor launches only the packaged worker through the strict manifest path; no legacy broad-root or unsandboxed fallback; bounded IPC, startup handshake, timeout, cancellation and process-tree cleanup preserved; adversarial manifest/package replacement tests; third-party connectors remain disabled until platform-specific filesystem and network boundaries are independently proven.

### C. Market-data evidence quality

- Public polling and WebSocket collectors exist, but venue-specific protocol correctness and physical-PC freshness/reconnect behavior still require exact validation.
- Polling response timestamps are not proof of one-way network latency. Lead/lag candidates must remain research-only unless synchronized event streams, sequence continuity and clock methodology are validated.
- A green CI run does not prove continuous collection on the owner's PC or profitability.

**Acceptance:** per-venue and per-symbol freshness, source and receive timestamps, sequence-gap handling where supported, reconnect/resubscribe, stale-feed fail-closed behavior, durable raw/normalized observations, data lineage, duplicate handling, storage growth/retention and reproducible chronological OOS replay including fees, spread, slippage, funding and other venue costs.

### D. Minimal command cockpit

The backend has an authenticated assistant gateway and an existing Virtual Office prototype, but this is not equivalent to a durable general task-control plane. The cockpit must remain a client of the headless engine.

**Minimum VST cockpit contract:**
- authenticated health/status and mode;
- collector and venue health with freshness;
- PAPER positions, fills, P&L and reconciliation;
- Learning Vault/evidence/readiness summaries;
- research/task submission and durable task ID, status, timestamps, result and blockers;
- start/pause/resume/stop PAPER through existing server guards only;
- clear UNKNOWN/STALE/OFFLINE/BLOCKED states;
- no credential entry in chat or mobile;
- no generic financial command endpoint and no REAL controls.

### E. Installation proof

Windows EXE/installer lifecycle has CI evidence, not physical-PC evidence. The old target PC, its available RAM/CPU/storage, local startup, long-running collector stability, restart recovery and actual data persistence remain unverified. Do not label the installation ready until a local evidence report exists.

## Delivery order

1. **Read-only account onboarding (Binance Spot + OKX Spot):** connect the existing DPAPI vault to a dedicated owner-only API and secure PC form; implement provider permission probes and a narrow read-only client; keep it disabled until tests pass.
2. **Production connector supervisor:** launch only the packaged worker inside the strict Linux Bubblewrap runtime; fail closed elsewhere until equivalent isolation is proven. Keep the registry disconnected from untrusted adapters.
3. **Continuous data/evidence loop:** validate market feeds and account snapshots, persist provenance/freshness, and ensure private account data stays owner-local and never enters shared learning.
4. **PC install validation:** exact-main installer artifact, backup-first install, PAPER startup, health, collector data, Learning Vault persistence, restart/recovery and resource measurements on the actual target PC.
5. **Minimum cockpit adapter:** implement the VST-specific Office Kit adapter only against stable, authenticated VST contracts. Office Kit must not own engine lifecycle, credentials, risk, learning or financial authority.

## Explicit non-goals for these increments

- No LIVE trading, order placement, cancellation, transfer or withdrawal.
- No request for exchange credentials until the secure owner-only flow and exact-head tests are complete.
- No third-party connector execution.
- No secret, balance, position or private account payload in cloud rendezvous, shared learning, CI artifacts, chat, logs or Office Kit.
- No claim of profitability or automatic promotion based on a sample-count threshold alone.
- No physical-PC test claimed from GitHub Actions.

## Definition of a useful first installation

The first installation is successful when the headless brain can run PAPER continuously, collect and validate public market data, preserve its learning/evidence state across restart, expose authenticated status and research controls, and report resource/health failures honestly. Private account ingestion is a separate opt-in milestone after the secure read-only path passes. REAL remains a future, separately reviewed decision and is never enabled by accumulated data alone.
