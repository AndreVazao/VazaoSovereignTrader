# Family learning, private connectivity and deployment roadmap

**Updated:** 2026-11-08  
**Status:** requirements and guardrails; not authorization to provision services, access private credentials or enable REAL.

## Priority order

1. Stabilize and physically validate the headless trading/research brain.
2. Preserve continuous public Market Data, Radar and durable PAPER observations.
3. Prove the complete evidence chain: Market Data → validation → Radar → strategy → risk → PAPER → telemetry.
4. Prove repeatable, long-running PAPER results with realistic fees, spread, slippage, liquidity, latency, regime coverage and out-of-sample validation.
5. Complete install/upgrade/recovery and Learning Vault continuity on the target PC.
6. Add private phone-to-PC connectivity and secure remote approvals only after local runtime and authentication gates pass.
7. Resume visual-office expansion after the brain is installable and testable.

REAL remains disabled by default. A score, timer, research result, successful test or capital target cannot automatically enable REAL.

## User and organization isolation

The intended family model may support separate owners and installations. Every owner retains isolated:
- Exchange credentials, account identifiers, balances, positions, orders, fills and transfers.
- Strategies, risk settings, private research, diagnostics and logs.
- Device pairing, sessions, approvals and revocation state.

Shared learning is a separate, explicit channel. Only approved, sanitized research artifacts may cross owner boundaries. Artifacts require canonical payload digests, verified provenance, producer/version identity, timestamps, validation/holdout details, quality state and permitted-use metadata. Receivers must reject revoked, stale, malformed, incompatible or unverified evidence.

The current repository contains canonical JSON and signed provenance implementation paths. This does not certify that a production database, organization enrollment or live family deployment is configured. Production migrations and external provisioning require separate review and authorization.

## Private connectivity and discovery

- Tailscale is the preferred direct private network path.
- A lightweight rendezvous service (Vercel may be considered) is optional discovery metadata only; it is not the trading engine, execution plane or authority for identity.
- Never expose the local runtime API directly to the public Internet.
- Device identity must be cryptographic and owner-scoped; IP addresses are routing hints only.
- Endpoint leases must expire, refresh on meaningful lifecycle/network changes, and support revocation. Avoid high-frequency polling that creates cost or dependency.
- Discovery metadata must not contain exchange secrets, balances, orders, positions, private strategies or chat history.
- Local Market Data and PAPER loops must continue when phone, Tailscale, Vercel or internet connectivity is unavailable.

## Remote control safety

A research request is not a financial approval. Remote actions must be bound to the exact owner, device, action, parameters, expiry and nonce. Passwords and MFA codes must not enter chat history, logs or notifications. Unknown outcomes require reconciliation; no blind retries. Orders, cancellations, risk changes, withdrawals and transfers are separate action classes with separate authorization.

The local API currently uses loopback `127.0.0.1:8765` and a local token. Neither the token nor private endpoints may be published or embedded in public rendezvous records.

## Deployment and portability

- First target: the user's older Windows PC, with a conservative resource profile.
- Preserve the same brain contracts on stronger Windows machines and Linux; scale compute budgets only when actual resources permit.
- Installer upgrades must preserve the Learning Vault; uninstall behavior must be explicit and tested.
- Android remains a remote client, not a dependency of the backend.
- Do not let the visual office or browser renderer block headless runtime operation.
- Keep Windows EXE, Android APK and future Linux packaging pipelines independently validated.

## Cabin Freight Trade and external references

Use Cabin Freight Trade, Freqtrade, Hummingbot, CCXT and NautilusTrader only as architecture/feature references after identifying exact source, license and behavior. Do not copy proprietary code or assume an upstream implementation is safe for VST. Design VST-native adapters and contracts, retaining exchange-specific capabilities and failure semantics.

## Known validation boundaries

- The user has already verified public Binance ticker and OHLCV access on the old PC. This does not certify the full Market Data-to-PAPER pipeline.
- The old PC has limited RAM; the full test suite previously exhausted the available memory. Use bounded, focused suites and avoid heavy tests on the physical PC until resource impact is known.
- Android emulator/Maestro checks are useful but do not replace physical-phone launch, rendering and logcat checks.
- CI installer lifecycle checks passed on PR #547, including upgrade and Learning Vault preservation. This does not prove installation on the user's physical PC.
- Vercel preview status is not a code test. Snyk quota exhaustion must not block code validation; still review security-sensitive changes with tests and source analysis.

## Current execution boundary

PAPER/read-only only. No live orders, REAL API credential activation, transfers, withdrawals, paid infrastructure provisioning or production database migration are authorized by this roadmap.
