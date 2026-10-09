# REAL client-order identity boundary — 2026-10-09

## Finding

`OrderManager` already required an execution authorizer for REAL orders, but the generic boundary still allowed an authorized caller to submit a REAL order without a non-empty `client_order_id`. In that case it could fall back to a legacy adapter method without deterministic identity. The primary engine authorizer separately checked identity, but relying only on a caller callback made the boundary weaker than its contract.

## Change

- `OrderManager` now rejects REAL submissions whose client-order identity is missing, empty, or whitespace-only.
- Rejection happens before the authorizer callback and before the exchange adapter, so the rejected path has no external side effect.
- PAPER simulation remains compatible and does not require an identity.
- Added a static AST contract test: direct CCXT order-submission calls in `PC_ENGINE` must remain confined to the reviewed `CcxtExchangeClient` wrappers. A new direct call elsewhere fails the test and forces an explicit boundary review.

## Validation

- Focused regression set: **25 passed in 10.76s**.
- `py_compile` passed for the changed production/test modules.
- `git diff --check` passed.
- No live exchange or external order endpoint was contacted.

## Safety

This is a defensive boundary hardening change. It does not authorize REAL, change any live configuration, call an exchange, or submit/cancel orders. REAL remains blocked by default; ambiguity remains fail-closed.
