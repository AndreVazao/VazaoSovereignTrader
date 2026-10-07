# REAL RELEASE GATE — VazaoSovereignTrader

Date: 2026-10-07

This checklist is the final software release gate for any future explicit human-controlled REAL activation. It does **not** authorize REAL trading.

## Gate A — Authorization integrity
- SAFE_MODE can only be cleared by `recover_from_safe_mode()`.
- REAL caller paths require scoped authorization and one-shot guard consumption.
- The final adapter boundary requires `REAL_ACTIVE`, `real_operational`, valid side/quantity, and durable client order identity.
- Startup cannot inherit REAL from configuration.

## Gate B — Deterministic controlled runtime
- Controlled adapter BUY path exercised without a real venue.
- Controlled adapter SELL path exercised without a real venue.
- ExecutionGate blocks adapter calls unless state is `REAL_ACTIVE`.
- Execution intents are durable before the external side-effect boundary.
- Confirmed fills create/remove positions without pending-order leakage.

## Gate C — Ambiguous outcome and recovery
- Adapter exceptions normalize to `UNKNOWN_OUTCOME`.
- UNKNOWN_OUTCOME retains durable execution intent and enters SAFE_MODE.
- Pending/partial recovery preserves cumulative observed fill, fee, notional, and client identity.
- Restart recovery resolves exact recorded venue/order identity and never blind-retries UNKNOWN.
- Controlled restart/recovery E2E now proves `execution_intent -> simulated process death -> exact client identity -> authoritative reconciliation -> safe intent cleanup`.
- Ledger/reconciliation paths are idempotent and fail closed on invariant violations.

## Gate D — Freshness and reconciliation
- REAL start requires authoritative account reconciliation before RUNNING.
- Risk, opportunity, exchange, and market-data freshness gates are evaluated immediately before order submission.
- Financial invariants are checked before pending-order accounting is committed.

## Gate E — Validation evidence
- Controlled REAL runtime E2E: **2 passed**.
- Controlled restart/recovery E2E: **2 passed**.
- Combined restart/runtime/recovery checkpoint: **12 passed in 6.67s**.
- Current authorization/execution/recovery focused checkpoint: **23 passed in 12.22s**.
- Previous external-side-effect regression: **56 passed**.
- Previous UNKNOWN/crash-window regression: **26 passed**.
- Previous SAFE_MODE/recovery authorization suite: **21 passed, 6 deselected**.
- `git diff --check` clean.
- Production modules and the new E2E test compile successfully.
- The broader `test_account_reconciliation.py` invocation remains known to stall on Windows; it is not claimed green.

## Release blocker

**REAL remains disabled until the final human authorization step is explicitly performed by the operator through the protected control path.** Green software validation is not authorization.

Final activation sequence:
1. Confirm release evidence is current.
2. Confirm authoritative, fresh account reconciliation.
3. Confirm readiness, timing, risk, and venue gates are green.
4. Confirm the operator understands that the next action can create real financial side effects.
5. Operator explicitly authorizes REAL through the protected control path.
6. Activate REAL only through the guarded state transition.

Any UNKNOWN, stale, ambiguous, mismatched, unavailable, or unreconciled condition aborts the sequence and keeps the system fail-closed.