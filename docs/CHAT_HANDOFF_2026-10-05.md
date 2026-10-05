# VazaoSovereignTrader — Chat Handoff — 2026-10-05

## Mission
Build the VazaoSovereignTrader as a multi-venue, auditable, fail-closed trading system. PAPER/read-only is the default. No live orders, real capital transfers, production migrations, paid deployments, or claims of profitability without explicit authorization and verified readiness.

## Repository / branch
- Repo: AndreVazao/VazaoSovereignTrader
- Main: main
- Active audit branch: audit/real-capital-execution-boundaries
- PR: #337 — draft, open, unmerged
- Latest source head before this handoff: 23b4e479a47de0d8c7aa37c8aea9d4052f4c59b6
- Documentation update added after CI review: a2a06b099b679460a96257ce6b9bf90d1cb20f3b

## Immediate CI truth
For head 23b4e479a47de0d8c7aa37c8aea9d4052f4c59b6:
- Python tests run 37223364512: FAILURE — 836 passed, 2 failed, 44 subtests passed.
- Windows EXE run 37223364514: SUCCESS — build-exe and build-installer passed.
- Therefore the current head is NOT green and must not be described as validated/merge-ready.

Failures:
1. tests/test_closed_order_recovery.py::test_execution_intent_recovers_historical_closed_order_by_exact_client_id
   - Complete historical closed-order evidence was returned, but recovery kept the execution intent instead of promoting the order to pending reconciliation.
   - Fix must preserve the rule that reconciliation, not recovery heuristics, is the source of truth for applying fills.
2. tests/test_recovery_pending_orders.py::test_recovery_execution_intent_blocks_engine_start
   - Minimal startup fixture reached _persist_recovery() without a recovery attribute.
   - Make the recovery/startup contract explicit; do not weaken production fail-safe behavior merely to satisfy the fixture.

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
1. Inspect/fix both failing recovery tests.
2. Re-run Python tests and Windows workflow for the new exact head.
3. Audit exactly-once semantics across crash windows: external submission, pending persistence, position mutation, ledger write, and recovery persistence.
4. Audit _recover_unresolved_execution_intents() and _reconcile_pending_orders() together for terminal/historical orders, partial fills, cumulative fill deltas, fees, venue identity, and restart behavior.
5. Add adapter contract tests for normalized symbol/side/amount/clientOrderId/status/filled/fee denomination and venue identity.
6. Perform end-to-end safe-mode/recovery tests for stale feed, watchdog, risk breach, adapter timeout, unknown order result, partial fill, process restart, and reconciliation mismatch.
7. Audit the complete REAL path: human authorization -> readiness freshness -> preflight -> reconciliation -> risk -> venue health/freshness -> execution gate -> adapter -> persistence -> recovery.
8. Only after evidence is clean consider PR review/merge. Keep PR draft until then.

## Product architecture reminders
- PC is the local control centre.
- Cloud/Vercel is for coordination/synchronization/learning, not autonomous control of local trading.
- Android can be paired to PC by USB for initial setup, then private connectivity such as Tailscale may be used.
- Target venues include Binance, OKX, Kraken, XTB, LiteFinance, YouHodler and others, subject to official APIs/terms and technical feasibility.
- Lead/lag research measures feed timing, price/volume differences, latency, spread/slippage and executable edge; no guaranteed profit.
- Capital ladder and transfers remain research/specification territory until every adapter and reconciliation path is proven safe.
