# VazaoSovereignTrader — Chat Handoff — 2026-10-05

## Mission
Build the VazaoSovereignTrader as a multi-venue, auditable, fail-closed trading system. PAPER/read-only is the default. No live orders, real capital transfers, production migrations, paid deployments, or claims of profitability without explicit authorization and verified readiness.

## Repository / branch
- Repo: AndreVazao/VazaoSovereignTrader
- Main: main
- Active audit branch: audit/real-capital-execution-boundaries
- PR: #337 — draft, open, unmerged
- Latest validated source head: `7ce2ad167c1c57e9046fb123293ee9312b958db9`
- Documentation commits may advance the branch after that source head; always use CI against the exact source commit when claiming validation.

## CI truth — exact latest source head
- Python tests run 37293839033: **SUCCESS** — test job completed successfully.
- Windows EXE run 37293838997: **SUCCESS** — build-exe + EXE smoke test + build-installer + installer smoke test all completed successfully.
- This validates source commit `7ce2ad167c1c57e9046fb123293ee9312b958db9`. It does **not** certify REAL-trading readiness.

## Durable reconciliation now validated
- RecoveryManager has a separate durable reconciliation journal schema; runtime state schema remains stable.
- Reconciliation prepares a complete target state before live in-memory mutation.
- Snapshot persistence is atomic/durable; ledger records carry deterministic reconciliation keys and use idempotent commit semantics.
- Startup recovery detects an unfinished reconciliation journal, commits the intended target, finishes ledger side effects idempotently, and clears the journal.
- Partial fills remain pending until reconciliation; terminal orders require valid cumulative fill evidence.
- Historical closed-order recovery never applies fills directly; it routes through pending reconciliation.
- Venue identity remains bound to the persisted execution intent; no silent fallback to another venue.
- Minimal compatibility fixtures are tolerated without weakening production fail-closed behavior.
- PAPER exchange startup no longer blocks on market discovery; live market loading remains isolated to non-PAPER paths.

## Already implemented in PR #337
- Missing/empty capital-transfer reconciliation evidence fails closed.
- UNKNOWN_OUTCOME added for ambiguous transfer submission.
- Transfer state is durably recorded as SUBMITTED before adapter call; ambiguous outcomes are not blindly resubmitted.
- Positive venue verification is required before transfer confirmation/accounting.
- ExecutionFabric requires explicit per-intent authorization callback and fails closed if missing/false/exception.
- CapitalTransferExecutionBridge requires explicit transfer authorization callback.
- REAL mode requires freshly consumed human authorization even with autonomous=True.
- Safe-mode/recovery gate unit coverage added.
- Repeated transfer reconciliation is tested for exactly-once accounting.
- Pending/partial buy/sell results no longer mutate positions immediately; fill application is deferred to pending-order reconciliation.
- Terminal order evidence without cumulative filled quantity fails closed and retains the pending order.
- Malformed execution intents and identity mismatches fail closed and remain unresolved.
- Historical intent recovery does not assume fills.
- Recovery uses the intent's recorded venue, not blindly the main venue.
- Pending-order venue resolution accepts exact adapter name when mapping key differs, but never falls back to another venue.
- Non-zero fees without explicit currency, non-quote fees, negative/non-finite fees fail closed; quote-denominated fees require matching quote currency.

## Key files
- PC_ENGINE/core/engine.py
- PC_ENGINE/core/recovery.py
- PC_ENGINE/storage/ledger.py
- PC_ENGINE/core/execution_fabric.py
- PC_ENGINE/core/execution_gate.py
- PC_ENGINE/core/real_mode_guard.py
- PC_ENGINE/core/real_readiness.py
- PC_ENGINE/core/real_readiness_service.py
- PC_ENGINE/core/capital_transfer_execution.py
- PC_ENGINE/core/capital_transfer_state.py
- PC_ENGINE/core/capital_transfer_reconciliation.py
- PC_ENGINE/core/capital_transfer_accounting.py
- PC_ENGINE/core/risk.py
- PC_ENGINE/radar/lead_lag_learning.py
- PC_ENGINE/radar/hot_path.py
- PC_ENGINE/opportunity/registry.py
- docs/REAL_CAPITAL_EXECUTION_AUDIT_2026-10-04.md
- docs/OPPORTUNITY_DISCOVERY_AND_CAPITAL_LADDER.md
- docs/OPPORTUNITY_REGISTRY.md
- docs/MASTER_ROADMAP_AND_AGREEMENTS.md

## Next execution order
1. Audit the complete REAL caller/path inventory: human authorization -> readiness freshness -> preflight -> reconciliation -> risk -> venue health/freshness -> execution gate -> adapter -> persistence -> recovery.
2. Add/finish adapter contract tests for normalized symbol/side/amount/clientOrderId/status/filled/fee denomination and venue identity.
3. Expand end-to-end safe-mode/recovery tests for stale feed, watchdog, risk breach, adapter timeout, unknown order result, partial fill, process restart, and reconciliation mismatch.
4. Review durable reconciliation for strict filesystem durability (including journal-clear directory fsync) and single-writer/idempotency concurrency assumptions.
5. Only after evidence is clean consider PR review/merge. Keep PR draft until then.
6. After REAL audit is structurally clean, return to research roadmap: AMD contextual feature first, then isolated Vibe-Trading sandbox, optional prediction-market observer.

## Product architecture reminders
- PC is the local control centre.
- Cloud/Vercel is for coordination/synchronization/learning, not autonomous control of local trading.
- Android can be paired to PC by USB for initial setup, then private connectivity such as Tailscale may be used.
- Target venues include Binance, OKX, Kraken, XTB, LiteFinance, YouHodler and others, subject to official APIs/terms and technical feasibility.
- Lead/lag research measures feed timing, price/volume differences, latency, spread/slippage and executable edge; no guaranteed profit.
- Capital ladder and transfers remain research/specification territory until every adapter and reconciliation path is proven safe.
