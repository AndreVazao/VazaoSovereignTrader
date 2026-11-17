# Universal Connector Runtime — VST

**Status date:** 2026-11-16  
**Scope:** first-party public market-data adapters only. This document describes implemented behavior, not a promise that every platform connector is already available.

## Implemented

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

## Safety boundary

The current registry can execute only capabilities in `READ_ONLY_CAPABILITIES`. It rejects order creation/cancellation, transfers, withdrawals, profile mutation and interactive device control. The public CCXT adapter exposes only:

- `public_market_data.read` with `operation=ticker`
- `public_market_data.read` with `operation=ohlcv`
- `public_market_data.read` with `operation=order_book`

The connector runtime does not connect private exchange accounts and does not grant trading authority. VST remains PAPER-only. A configured venue is an owner-selected public-data source, not proof that its remote API is reachable. The manifest health value means the local adapter is loaded; remote connectivity must be read from Radar/market-data health telemetry.

## Limits and next phases

- The registry is in-process. The manifest timeout is passed to the adapter and CCXT's request timeout is set, but Python cannot forcibly interrupt arbitrary synchronous third-party code. Do not load untrusted adapters into this process.
- A one-shot spawned-process wrapper now exists in `PC_ENGINE/core/isolated_connector_worker.py`. It uses strict JSON IPC, caps request/response sizes, applies a bounded wait and terminates the worker process tree on completion or timeout: POSIX workers enter a dedicated session/process group which the parent kills, while Windows workers are held in a kill-on-close Job Object that is closed before waiting for exit. Focused tests verify that a subprocess spawned by an adapter cannot outlive its worker timeout. This is groundwork only; it is not wired into the live registry or enabled for providers.
- The worker now applies OS-enforced resource ceilings before adapter code runs: POSIX `RLIMIT_AS` and `RLIMIT_CPU`, or a Windows Job Object with per-process memory and CPU-time limits plus kill-on-close. If the required platform limits cannot be installed, the worker fails closed. The worker also removes credential-shaped environment variables before invoking the adapter factory. POSIX limits are calculated against both inherited soft and hard ceilings; the worker never raises either inherited limit. A regression test covers an inherited soft memory/CPU ceiling stricter than the VST-requested budget. This last correction is awaiting exact-HEAD CI.
- These controls bound worker memory and CPU time; they do not isolate filesystem access, restrict network egress, prevent access to other files owned by the same user, or provide a complete security sandbox. Do not load untrusted third-party code through it. Filesystem isolation, provider-specific network allowlists, stronger supervision/incident telemetry and Windows/Linux lifecycle validation remain prerequisites before production plugin execution.
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

CI results for a PR must be checked against its exact head SHA. CI does not replace physical Windows, Linux or Android validation.
