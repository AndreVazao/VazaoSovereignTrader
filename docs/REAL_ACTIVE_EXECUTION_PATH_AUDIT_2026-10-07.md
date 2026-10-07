# REAL_ACTIVE Execution Path Audit — 2026-10-07

## Scope
Audit of the production REAL path from guarded REAL activation through order side-effect, crash recovery, reconciliation, ledger accounting, and capital-transfer execution. No live order, transfer, or capital operation was executed.

## Confirmed chain
1. REAL entry requires fresh `RealModeGuard` authorization consumption and guarded `ExecutionGate` activation.
2. `start()` in REAL performs preflight, unresolved execution-intent recovery, and authoritative account reconciliation before setting runtime status to `RUNNING`; only then is `real_operational=True`.
3. `_open_position()` and `_close_position()` call `ExecutionGate.can_submit()` immediately before invoking `OrderManager`.
4. `OrderManager` has a mandatory REAL execution authorizer immediately before the exchange adapter call. The callback requires `ExecutionState.REAL_ACTIVE`, `real_operational=True`, valid side/quantity, and a non-empty client order identity.
5. Every engine order receives a durable `client_order_id` and persists an `execution_intent` before the external side effect.
6. Exchange responses are normalized; an unconfirmed/non-terminal order is not treated as filled. It enters `pending_orders` and SAFE_MODE/reconciliation handling.
7. Restart recovery resolves an execution intent only against its recorded venue and exact symbol/side/quantity/client identity; ambiguity keeps the system fail-closed.
8. Pending-order reconciliation uses cumulative fills, financial invariants, deterministic reconciliation keys, and idempotent ledger writes. Partial fills are not double-booked.
9. Direct `ccxt.create_order()` production reachability is limited to `CcxtExchangeClient`, called from `OrderManager`; no second production order submission path was found.
10. Capital transfer execution independently requires owner isolation, journal reservation, explicit transfer authorization, durable SUBMITTED state before adapter invocation, and UNKNOWN_OUTCOME on ambiguous/exceptional post-submission results. UNKNOWN is not retryable.
11. Browser live execution remains separately disabled/config-gated and is not wired as a second engine order path; its own connector still requires explicit live enablement and confirmation.

## Fail-safe findings
- No production REAL side-effect bypass was found in the audited chain.
- `ExecutionFabric` is independently fail-closed with per-intent authorization, owner isolation and mandatory idempotency key, but the current engine's primary exchange path uses `OrderManager` rather than Fabric.
- SAFE_MODE clearing remains restricted to `recover_from_safe_mode()`.

## Validation
- `tests/test_order_manager_execution_authorization.py`
- `tests/test_order_manager.py`
- `tests/test_execution_fabric.py`
- `tests/test_execution_gate_integration.py`
- Result: **8 passed, 7 deselected in 7.60s**
- `py_compile` passed for audited production modules.
- `git diff --check` passed.
- Full account-reconciliation suite remains known to stall on Windows and is not considered green.

## Residual hardening backlog
- Add explicit static/contract coverage proving every future external side-effect adapter is reachable only through an authorization boundary.
- Add focused tests for crash timing between external acceptance and persistence, including client-order lookup ambiguity.
- Continue audit of cancellation/withdrawal/transfer API callers and browser/Android execution-surface wiring before any REAL enablement decision.

## Safety status
REAL execution was not enabled or exercised during this audit. No capital was moved and no live order was submitted.
