# REAL execution crash-window hardening — 2026-10-07

## Objective

Close the failure window where a venue may accept an order but the process loses the response before durable post-submit state is recorded.

## Finding

The primary engine path already persisted `execution_intents` before calling `OrderManager`. However, `OrderManager` previously converted an exception raised during the external adapter call into a normal `ERROR` result. The engine then removed the execution intent as if the order had been rejected.

That could lose the only durable identity needed to reconcile a venue-side order after restart.

## Hardening implemented

1. External adapter exceptions now normalize to `UNKNOWN_OUTCOME`.
2. Adapter response contract violations after the external call also normalize to `UNKNOWN_OUTCOME`.
3. REAL engine buy/sell paths retain the durable `execution_intent` for `UNKNOWN_OUTCOME` and enter `SAFE_MODE`.
4. The intent keeps the exact `client_order_id`, venue, symbol, side, quantity and creation timestamp.
5. Restart/recovery therefore resolves the exact recorded identity instead of retrying blindly.
6. Immediate adapter responses with a conflicting `clientOrderId` are rejected as an unsafe contract mismatch.
7. Duplicate dead `_ticker_is_fresh`/`_open_position`/`_close_position` implementations were removed so the execution path has one authoritative implementation.

## Required recovery behavior

- `UNKNOWN_OUTCOME` is never treated as a rejection.
- No automatic resubmission occurs.
- `SAFE_MODE` remains latched until the existing explicit recovery contract succeeds.
- Recovery must resolve the exact venue/client identity or remain blocked.

## Validation

Focused regression suite: **26 passed**.

Covered areas include:
- adapter normalization and identity mismatch
- REAL OrderManager authorization boundary
- ambiguous exchange outcome handling
- execution-intent recovery
- closed-order recovery
- deterministic client-order identity
- pending/partial reconciliation
- execution gate integration

Additional validation:
- duplicate-method AST audit: no duplicate methods remain in `SovereignEngine`
- `py_compile` passed for the hardened production modules
- `git diff --check` passed

## REAL safety status

No REAL order, capital transfer, withdrawal, or paid service was executed during this hardening. The production system remains PAPER-first and fail-closed.

## Next hardening block

- complete static/contract coverage for every external side-effect adapter
- finish cancellation/capital-movement caller audit
- complete Browser/Android execution-surface audit
- exercise restart/reconciliation contracts with deterministic integration doubles
- only after all gates are independently green should a human-controlled REAL enablement procedure be considered
