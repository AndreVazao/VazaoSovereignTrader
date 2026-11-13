# Universal Connector Runtime — VST

**Status date:** 2026-11-13  
**Scope:** first-party public market-data adapters only. This document describes implemented behavior, not a promise that every platform connector is already available.

## Implemented

- A typed provider manifest and capability contract lives in `PC_ENGINE/core/platform_connectors.py`.
- `ConnectorRegistry` enforces explicit owner grants and provider verification, read-only capability allowlists, per-provider rolling request limits, JSON request/response size limits, detached request data and sanitized adapter errors.
- The first built-in adapter is `CcxtPublicMarketDataAdapter`. It supports bounded public `ticker`, `ohlcv` and `order_book` reads without API keys or private/account methods.
- The engine registers only venues explicitly present in `radar.polling_exchanges`, while the engine is in PAPER mode and the Radar is observational-only.
- Registered adapters reuse the existing unauthenticated `MarketRadar` CCXT clients and their per-client locks. The registry therefore does not create a second set of exchange sessions on a constrained PC.
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
- Process isolation, crash supervision and resource leases for third-party providers are still required before enabling external/plugin adapters.
- OAuth, private account reads, balances, statements, Android UI automation, browser automation and desktop automation are contract categories only; they are not live integrations in this increment.
- U-Hodler is not connected. No Android virtualization provider is provisioned locally or in cloud.
- Provider-specific terms, permissions and authentication flows must be reviewed before adding any non-public capability. Human handoff remains mandatory for MFA, OTP, CAPTCHA, biometrics, consent and financial/security prompts.

## Verification

The implementation is covered by unit tests for:

- configured-venue allowlisting and fail-closed registration;
- reuse of the existing MarketRadar client and lock;
- read-only capability enforcement;
- authentication, request bounds, credential-field rejection and no-store responses;
- rate limiting and rejection of reads during collector shutdown.

CI results for a PR must be checked against its exact head SHA. CI does not replace physical Windows, Linux or Android validation.
