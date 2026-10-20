# Independent trading-project reuse shortlist

**Reviewed:** 2026-10-20  
**Scope:** identify useful public projects for Sovereign Trader research and possible lawful component reuse. This is a preliminary engineering/licensing screen, not legal advice or a full dependency/provenance audit.

## Decision rule

Do not copy code just because a project is public or used privately. For every proposed reused file/component, record its exact upstream URL and commit/tag, copyright owner, licence text, transitive/runtime dependencies, notices required, modifications, and intended distribution (including family devices, APK/EXE, and any source sharing). Keep a software bill of materials and a third-party notices file. If provenance or licensing is unclear, do not import it. Changing names or rewriting superficial syntax does not make copied implementation independent.

A permissive licence is not “no licence”: MIT generally requires retaining copyright and permission notices; Apache-2.0 has notice, licence, and patent-related terms. Confirm compatibility with the exact component and all dependencies before adoption.

## Candidate screen

| Project | Licence observed in repository | Potential learning/reuse area | Initial recommendation |
|---|---|---|---|
| [Hummingbot](https://github.com/hummingbot/hummingbot) | Apache-2.0 in its root LICENSE | Multi-venue connector model, connector lifecycle/health, market-making and strategy/execution separation | High-priority architecture study. Any code reuse only after per-file/dependency audit and preserving Apache notices. Do not transplant the framework wholesale. |
| [Jesse](https://github.com/jesse-ai/jesse) | MIT in root LICENSE | Research workflow, backtesting, strategy iteration and reporting | Study for research/backtest workflow. Selected code may be considered after dependency and provenance audit; preserve notices. |
| [LLM-Auto-Trader](https://github.com/Erfaniaa/LLM-Auto-Trader) | MIT in root LICENSE | LLM proposes, deterministic risk layer constrains; CCXT venue breadth; PAPER-first product shape | Study separation of language-model suggestions from deterministic controls. Treat as a small independent research candidate; audit exact files and dependencies before reuse. |
| [NautilusTrader](https://github.com/nautechsystems/nautilus_trader) | LGPL-3.0 in root LICENSE | Event-driven trading architecture, simulation/live consistency and data/event handling | Architecture study only initially. LGPL obligations and linking/distribution details need careful review before any integration. |
| [Freqtrade](https://github.com/freqtrade/freqtrade) | Upstream project is GPL-3.0 | Dry-run, historical data, backtesting, bias analysis and strategy evaluation | Requirements and conceptual study only for current clean-room plan; do not copy implementation into Sovereign Trader. |
| [AndreVazao/freqtrade](https://github.com/AndreVazao/freqtrade) | Root LICENSE currently contains only “Bot copiado para experiência.” | User's experimental mirror/fork history | Not a reliable licence grant. Do not treat this line as permission to relicense upstream content. |

CCXT is a widely used exchange-library reference, but this first pass did not establish the exact licence from its repository root; do not assume permission from popularity. Check the precise package/distribution and its licence before considering any dependency.

## What to learn and implement independently

1. **Venue capability registry:** each venue declares tested market-data modes, symbols/precision, order types, rate limits, fee/funding semantics, sandbox support, and recovery behavior. Unknown capabilities remain unavailable rather than guessed.
2. **Connector health and fault isolation:** per-venue connection state, data freshness, throttling, clock skew, reconnect/backoff, and clear degraded states. No connector may bypass the central execution gate.
3. **One authoritative PAPER/replay path:** reproducible datasets and manifests; simulated fills never appear as real account state; deterministic replay for regressions.
4. **Research validity gates:** chronological splits, walk-forward/out-of-sample evaluation, fees/slippage/funding, look-ahead and recursive-bias checks, sample size and uncertainty.
5. **LLM safety boundary:** model output is a proposal, never authority. Validate against typed schemas, permissions, risk limits and explicit human approval; natural language must not directly trigger an exchange side effect.
6. **Operational parity:** PC cockpit, virtual office and Android are clients of one authenticated API and one engine, with visible stale/offline/unauthorized/outcome-unknown states.
7. **Evidence ledger:** record data versions, model/strategy version, venue assumptions, test results, operator approvals and action outcomes.

## Suggested lab strategy

- Create a dedicated lab repository only after choosing a concrete experiment; keep it isolated from the production engine.
- First experiment: a small **venue-capability contract and fake-venue test harness**, using synthetic fixtures and no credentials. This tests connector health, rate limits, malformed/stale data and failure recovery without importing a trading framework.
- Second experiment: a reproducible PAPER replay/evaluation harness with explicit transaction costs and bias checks.
- Third experiment: LLM proposal-to-validated-plan adapter with no exchange side effects.
- Promote a lab result only via an explicit review, tests, provenance record and a single implementation PR. Do not open parallel implementation PRs while #389 is the active office/cockpit PR.

## Non-negotiable safety boundaries

- No real orders, withdrawals, transfers, or capital movement during these experiments.
- No exchange keys or owner tokens in client apps, browser local storage, URLs, screenshots, or logs.
- No public API exposure or paid/cloud resources without explicit approval.
- Keep Sovereign Trader's execution gates, SAFE_MODE, audit/evidence trail and REAL readiness protections authoritative.
- A successful unit test or PAPER simulation is not evidence of profitability or REAL readiness.
