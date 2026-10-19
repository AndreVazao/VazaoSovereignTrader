# Sovereign Trader — family learning, connectivity and execution roadmap

Date recorded: 2026-10-19
Scope: planning/documentation only. This document does not authorize trading changes, external service provisioning, credential changes, or a transition to REAL mode.

## Priority order

1. Stabilize the trading/research brain and evidence pipeline.
2. Establish repeatable, long-running PAPER simulations and durable, auditable history.
3. Prove data quality, realistic fees/slippage/latency, regime coverage, chronological out-of-sample validity, and dependence-aware effective sample size before using results to inform a REAL-readiness review.
4. Keep REAL disabled by default. Any later transition requires explicit owner review and independent risk/readiness gates; never promote automatically because a timer or score passed.
5. Keep the first dashboard simple and useful while preserving the mobile cockpit. A richer visual layer must not delay brain stability or PAPER evidence collection.

## Cabin Freight Trade — feature benchmarking, not copying

The owner has an existing trading bot called **Cabin Freight Trade** and wants it reviewed as a functional benchmark. The goal is to identify mature capabilities that could improve Sovereign Trader, particularly multi-exchange architecture, and then design equivalent capabilities that fit Sovereign Trader's own contracts, safety boundaries, and codebase.

- Do not copy the bot wholesale, copy proprietary code, or assume its implementation is safe or suitable.
- First identify the exact repository/source and inspect its documented behavior, supported venues, adapter boundaries, order lifecycle/reconciliation, market-data freshness, fees, risk controls, recovery, and tests.
- Produce a feature-by-feature gap analysis: capability, evidence in source/tests, value to Sovereign Trader, dependencies, safety implications, and proposed native implementation.
- Prioritize reusable concepts and independently designed interfaces/adapters. Preserve exchange-specific capabilities and constraints rather than pretending every exchange supports the same features.
- No credentials, live orders, or REAL-mode changes are needed for this review.

The source repository for Cabin Freight Trade was not identified during the current GitHub repository search; its exact URL/name must be confirmed before a source-level audit can be claimed.

## Virtual AI Office

Sovereign Trader is to have its own live Virtual AI Office, similar in concept to the office work planned for DGM-MAT, but specific to trading. A later visual dashboard should show agent/activity states and history for research, market analysis, strategy evaluation, risk review, PAPER execution, reconciliation, and reporting.

- Treat the office as an observability and explanation layer, not as authority to place orders.
- Show what each agent is doing, why it started, which evidence/data it used, what it concluded, and whether the result is pending, rejected, simulated, or verified.
- Clearly distinguish actual events from animation/storytelling; never imply that an agent performed work that logs do not support.
- Start with a simple status/activity view; richer animated characters and dashboard polish are a later phase after the brain and PAPER loop are reliable.
- Keep this project isolated from DGM-MAT in credentials, permissions, runtime and data ownership.

## PC/mobile rendezvous: Tailscale + Vercel

Goal: PC and mobile should discover each other without manually typing changing IP addresses, including when the owner is away from the PC. Tailscale is the preferred private connectivity path; Vercel may act as a lightweight rendezvous/control-plane service, not as a trading engine.

Desired design:
- Devices register an authenticated, owner-scoped endpoint/lease at a deliberately low frequency or on meaningful lifecycle/network changes, not via an aggressive always-on heartbeat.
- Registration should refresh/expire leases, record last-seen and capabilities, and support revocation. A short heartbeat must not be required just to keep the system discoverable.
- Use Tailscale identity/private routing for direct connections where available. Treat IP addresses as dynamic hints, not identities or durable secrets.
- Clients must tolerate offline devices, stale registrations, mobile sleep, network changes and unavailable Vercel; none of this may block the market-data/trading loop.
- Do not expose private Tailscale endpoints publicly. Do not put credentials, account details, private trading data or long-lived secrets in Vercel logs or public responses.
- Add signed/authenticated requests, replay protection, expiry, owner/device binding, rate limits and explicit tests for cross-owner leakage before enabling device discovery.

### Infrastructure finding from the 2026-10-19 remote audit

The repository's latest remote documentation records that the Vercel health route was reachable and the endpoint-lease route is deployed, but the connected Vercel project had **zero configured environment variables** and no active Trader/shared-learning Supabase project was found in the inspected Supabase account. Therefore authenticated, database-backed endpoint discovery and shared learning are **not verified production-ready**. Do not treat deployment status or an HTTP health response as proof of end-to-end device rendezvous. Recheck current configuration and regional/plan constraints read-only before wiring clients; provisioning resources requires explicit owner approval and a cost review.

## Family multi-user model: private trading, deliberately shared learning

The intended deployment is private/family use and may include the owner, a brother-in-law, and multiple users/devices. It is not intended as a public commercial service at this stage.

Hard data boundaries:
- Each user/owner has isolated identities, credentials, exchange accounts, balances, positions, orders, fills, strategies, risk settings, private logs, and personal configuration.
- One family member must not be able to inspect another member's trading activity or account data by default.
- Shared learning is a separate, explicit data product: only approved, sanitized research artifacts may cross owner boundaries, such as aggregate strategy observations, market-regime findings, feature definitions, and evidence summaries.
- Never share API keys, account identifiers, raw private orders/trades, balances, personal logs, or a user's unapproved strategy/configuration.
- Every shared artifact should carry provenance, version, timestamps, data-quality status, validation/holdout details, and permitted-use metadata. Receiving systems must be able to reject stale, low-quality, incompatible or poisoned evidence.
- The owner's central system is the coordinating knowledge hub, but central coordination must not silently grant access to private user data. Enforce owner-scoped authorization at the API and storage layers and test it.
- Do not let shared knowledge directly modify production strategy or activate REAL execution. Imported knowledge is a research input requiring local validation and the same PAPER/evidence gates.

## Current known gaps / acceptance criteria

- Audit temporal overlap and dependence between outcome samples; report effective sample size, not only raw sample count.
- Complete canonical multi-asset instrument and connector-capability schemas and a read-only per-venue inventory.
- Add read-only market-data adapters only after verifying supported platforms and regional/API constraints.
- Keep the virtual per-platform ledger and manual tier-review gates ahead of any real-capital consideration.
- Verify Tailscale + Vercel + database-backed rendezvous end-to-end with authenticated device identity, expiry, revocation, offline recovery and owner isolation.
- Add tests proving a user/device cannot read another owner's endpoints, accounts, orders or private logs, while only explicitly approved sanitized learning artifacts can be shared.
- Run durable PAPER simulations and preserve their evidence/history before any REAL-readiness decision.
- Record all claims as one of: implemented and tested, implemented but not integration-tested, planned, or blocked. Documentation alone is not proof of implementation.

## Execution boundary

This roadmap is not permission to submit orders, enable REAL, create paid infrastructure, provision a database, access exchange credentials, or change risk limits. Continue with read-only audits, offline tests, documentation and isolated PAPER work until a specific change is reviewed and validated.
