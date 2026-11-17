# Universal Connector Runtime — VST

**Status date:** 2026-11-17  
**Scope:** first-party public market-data adapters only. This document describes implemented behavior, not a promise that every platform connector is already available.

## Implemented on main

- A typed provider manifest and capability contract lives in `PC_ENGINE/core/platform_connectors.py`.
- `ConnectorRegistry` enforces explicit owner grants and provider verification, read-only capability allowlists, per-provider rolling request limits, JSON request/response size limits, detached request data and sanitized adapter errors.
- The first built-in adapter is `CcxtPublicMarketDataAdapter`. It supports bounded public `ticker`, `ohlcv` and `order_book` reads without API keys or private/account methods.
- The engine registers only venues explicitly present in `radar.polling_exchanges`, while the engine is in PAPER mode and the Radar is observational-only.
- Registered adapters reuse the existing unauthenticated `MarketRadar` CCXT clients and their per-client locks. The registry therefore does not create a second set of exchange sessions on a constrained PC.
- On-demand public connector reads are capped at 12 requests/minute per provider, in addition to CCXT's own rate limiter.
- The connector API is owner-authenticated with `read_private_state`:
  - `GET /connectors` returns safe connector metadata and local registration diagnostics.
  - `POST /connectors/{provider_id}/read` accepts only a read capability and a JSON request. It is a read operation despite using POST for a bounded request body.
- Connector reads are refused while the engine is not RUNNING or collector shutdown has begun. Responses are `no-store`.
- Credential-shaped fields are rejected before the request reaches an adapter. No credentials are loaded, copied, logged or persisted by this connector runtime.

## Worker resource boundary on main

PR #576 is merged in main at `f4b5811b59f71efcc4d2fcbcf3441efd05cb595e`:
- POSIX workers apply `RLIMIT_AS` and `RLIMIT_CPU`, preserving inherited soft and hard ceilings.
- Windows workers use a kill-on-close Job Object with per-process memory and CPU-time limits.
- POSIX process groups and Windows Job Objects terminate worker descendants on timeout.
- Credential-shaped inherited environment variables are removed before adapter factory execution.
- JSON IPC is bounded and worker errors are sanitized.
- If the required resource boundary cannot be established, the worker fails closed.

These controls bound resource consumption and process lifetime; they do not isolate filesystem access or restrict network egress. They do not prevent code from reading other files owned by the same host user.

## Linux sandbox prototype in PR #577

The current draft PR adds a Bubblewrap command builder with:
- Separate user, PID, IPC, UTS and network namespaces; network is denied entirely.
- A cleared environment and selected read-only runtime roots.
- Private, size-bounded `/tmp` and `/work` tmpfs mounts.
- Validation of executable paths, runtime roots, tmpfs sizes and Bubblewrap availability.
- A dedicated Linux CI workflow intended to execute negative tests for host-file access, loopback network access and tmpfs size.

This is not yet a production sandbox:
- The command builder is not integrated with `IsolatedConnectorAdapter` or `ConnectorRegistry`.
- Real Bubblewrap CI must pass on the exact current PR HEAD.
- Filesystem adversarial tests, cleanup/supervision and provider-specific HTTPS egress policy remain incomplete.
- Windows filesystem/network isolation is not implemented.
- The worker remains disconnected from the live connector registry. Do not load untrusted third-party adapters.

## Safety boundary

The current registry can execute only capabilities in `READ_ONLY_CAPABILITIES`. It rejects order creation/cancellation, transfers, withdrawals, profile mutation and interactive device control. The public CCXT adapter exposes only:
- `public_market_data.read` with `operation=ticker`
- `public_market_data.read` with `operation=ohlcv`
- `public_market_data.read` with `operation=order_book`

The connector runtime does not connect private exchange accounts and does not grant trading authority. VST remains PAPER-only. A configured venue is an owner-selected public-data source, not proof that its remote API is reachable. The manifest health value means the local adapter is loaded; remote connectivity must be read from Radar/market-data health telemetry.

## Other limits and next phases

- The registry is in-process. The manifest timeout is passed to the adapter and CCXT's request timeout is set, but Python cannot forcibly interrupt arbitrary synchronous third-party code. Do not load untrusted adapters into this process.
- The current wrapper starts a fresh process per read; it is a safety prototype, not yet an optimized persistent worker pool.
- OAuth, private account reads, balances, statements, Android UI automation, browser automation and desktop automation are contract categories only; they are not live integrations in this increment.
- U-Hodler is not connected. No Android virtualization provider is provisioned locally or in cloud.
- Provider-specific terms, permissions and authentication flows must be reviewed before adding any non-public capability. Human handoff remains mandatory for MFA, OTP, CAPTCHA, biometrics, consent and financial/security prompts.

## Verification

The implementation is covered by unit tests for:
- configured-venue allowlisting and fail-closed registration;
- reuse of the existing MarketRadar client and lock;
- read-only capability enforcement;
- authentication, request bounds, credential-field rejection and no-store responses;
- rate limiting and rejection of reads during collector shutdown;
- isolated-worker JSON IPC, timeout termination of the worker and its child processes, request/response bounds, credential-shaped environment cleanup and OS-enforced worker resource limits.

For PR #577, the dedicated Linux Bubblewrap workflow is an additional acceptance gate. CI results must be checked against the exact PR HEAD. CI does not replace physical Windows, Linux or Android validation.
