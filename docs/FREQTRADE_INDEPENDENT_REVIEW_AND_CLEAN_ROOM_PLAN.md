# Freqtrade review — independent feature extraction plan

**Reviewed:** 2026-10-20  
**Reference repository:** https://github.com/AndreVazao/freqtrade  
**Purpose:** learn from capabilities and product maturity without importing or copying implementation code into VazaoSovereignTrader.

## Important provenance and licensing finding

The `AndreVazao/freqtrade` repository's current `LICENSE` file contains only the sentence **"Bot copiado para experiência."** This is not a clear software licence grant, does not identify the copyright owner, and does not establish that the repository owner can relicense all content. Its README describes Freqtrade, a separate upstream project. The upstream Freqtrade project is GPL-3.0 licensed (see the upstream project's official repository and licence). The current fork's one-line LICENSE does not override upstream rights or establish permission to relicense copied code.

**Safe decision:** do not copy, port, translate, rename, or paste Freqtrade source code, tests, strategies, assets, docs, or distinctive implementation details into Sovereign Trader. Do not assume that removing attribution or changing names makes copying permissible. If future code reuse is specifically desired, first establish provenance for the exact file and obtain legal review of the applicable licence and distribution consequences. This document is an engineering risk assessment, not legal advice.

Official reference:
- Upstream Freqtrade: https://github.com/freqtrade/freqtrade
- Upstream licence: https://github.com/freqtrade/freqtrade/blob/develop/LICENSE
- The user-owned mirror/fork inspected: https://github.com/AndreVazao/freqtrade/blob/main/LICENSE

## What is worth learning at the product/requirements level

The README for the reference project describes multi-exchange support, dry-run, backtesting, historical data management, strategy optimization, performance reporting, and look-ahead / recursive-analysis checks. These are product capabilities and quality gates we can independently design and implement; no source-code reuse is required.

| Capability to study | Independent Sovereign Trader direction | Guardrail |
|---|---|---|
| Multi-exchange coverage | Venue capability registry, adapter contracts, exchange-specific health and feature matrix | Do not assume a venue works merely because CCXT lists it |
| Dry-run / PAPER | Same authoritative engine path with simulated fills and explicit provenance | Never mix simulated fills with real account/order state |
| Historical data & backtesting | Versioned market-data snapshots, reproducible replay and dataset manifests | Timestamp, gaps, exchange, fees, funding and data-quality checks |
| Strategy evaluation | Walk-forward/OOS, regime splits, transaction costs, latency and slippage stress | No promotion based on in-sample return alone |
| Look-ahead / recursive bias | Independent static and replay-based bias checks in research pipeline | A clean report is evidence, not an execution authorization |
| Performance reporting | Net metrics with drawdown, exposure, sample size, uncertainty and venue breakdown | No unsupported profit claims; include costs and limitations |
| Operational UI | Keep the existing engine/API authoritative; expose a common read model to PC, office and Android | Clients never own exchange secrets or bypass server risk controls |

## Fit against current Sovereign Trader architecture

The existing product already has substantial independent foundations that must be preserved: execution gates, owner/device authentication, mobile pairing, human-interaction bridge, research inbox, evidence ledger, venue health diagnostics, execution-surface catalog, PAPER evidence scorecard and a protected REAL readiness path. The office should surface these capabilities rather than creating a parallel bot or duplicating engine logic.

Current PC cockpit source is `PC_ENGINE/api/cockpit.py`; `PC_ENGINE/api/dashboard.py` aliases its HTML. It already contains operator controls, PAPER validation, REAL authorization/readiness, human-intervention, research submission, venue health, execution surfaces, evidence reports, ongoing PAPER study, diagnostics, assets, positions, models, logs and preflight. Before integrating the new office, build an explicit control/API inventory from the actual route handlers and existing tests; do not replace existing controls with placeholders.

## Prioritized independent implementation plan

1. **Capability inventory (read-only):** map every current cockpit card/control to its HTTP route, method, request/response shape, auth requirement, role/scope, server-side guard, audit record and test. Flag any route whose access semantics are unclear.
2. **Shared client read model:** typed response models for health, status, venue health, evidence freshness, pending human interactions and audit events; include timestamps, stale/offline/unauthorized states.
3. **Office parity:** make the left navigation and right conversation panel persistent, with each central department surfacing the same capabilities as the compact cockpit. Avoid duplicate command implementations.
4. **Conversation integration:** route natural-language requests only through the existing authenticated assistant gateway/research inbox. Distinguish queued, accepted, completed, failed and outcome-unknown states; never infer success from sending.
5. **Research quality gates:** plan independent look-ahead and recursive-indicator analysis, walk-forward/OOS and reproducible historical replay; use controlled/synthetic fixtures first.
6. **Venue adapter maturity:** compare each exchange's supported order types, precision, fees, rate limits, market-data modes, sandbox availability and recovery semantics using official docs and controlled adapters.
7. **Validation:** deterministic tests, stale/outage/revocation tests, Windows packaging checks, Android logcat retest and controlled adapter E2E. No real exchange order or capital movement for these steps.

## Out of scope for this increment

- No source code copied from Freqtrade.
- No exchange API keys or account login in the office/client.
- No REAL authorization changes, live orders, transfers, withdrawals or automated capital movement.
- No cloud deployment, paid service, public port or Vercel traffic proxy.
- No claim that this review proves the fork's entire source tree has clean provenance; a complete file-by-file provenance audit would be a separate task.

## Acceptance criteria

- The product keeps its own code, engine, execution safety and owner identity.
- Useful capabilities are captured as independent requirements and tests, not imported implementation.
- The office is a client of the same authoritative API as the PC cockpit and Android app.
- No Freqtrade code is added unless provenance and applicable licence permission are established for the exact material.
