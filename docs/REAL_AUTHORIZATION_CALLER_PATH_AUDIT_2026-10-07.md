# REAL Authorization / Caller Path Audit — 2026-10-07

## Scope
Audit all production callers that can arm, consume, activate or enter REAL mode after SAFE_MODE recovery hardening.

## Production caller inventory
- POST /real/arm: only trade_real scope; delegates phrase verification to RealModeGuard.arm().
- POST /real/disarm: only trade_real scope; disarms and fail-safes an active REAL engine.
- POST /start: when already in REAL, requires trade_real, blocks pending orders, performs authoritative account reconciliation and readiness checks, then consumes the one-time guard authorization before engine.start().
- POST /mode: when switching to REAL, requires trade_real, blocks open positions/pending orders, verifies the guard and now consumes the one-time authorization before engine.set_mode(). It then runs preflight, reconciliation and readiness; any failure enters REAL fail-safe.
- SovereignEngine._maybe_autonomous_real_promotion(): PAPER-only path; requires configured autonomous opt-in, fresh readiness, remembered initial human authorization, one-time guard authorization/consumption, then guarded REAL mode transition. SAFE_MODE is rejected before this path by the earlier mutation audit.
- recover_from_safe_mode(): does not manufacture REAL authorization. It requires explicit recovery confirmation, fresh internally generated evidence, and in REAL a fresh RealModeGuard.can_enable_real() authorization window before activating the execution gate.

## Guard invariants
- RealModeGuard.arm() is the only production operation that creates the initial human REAL authorization state.
- consume() is one-shot for the temporary arming window; consumption does not create a new authorization.
- ExecutionGate.activate_real() refuses activation without its own human-authorized state and eligible state transition.
- SovereignEngine.set_mode("REAL") rejects direct callers unless the guard records a freshly consumed authorization (last_reason == "authorization consumed").
- Startup remains PAPER-first; configured REAL is not restored automatically.

## Finding fixed in this checkpoint
The /mode REAL caller previously checked can_enable_real() but did not consume the authorization before calling set_mode(). Since set_mode() intentionally requires a freshly consumed authorization, this made the direct guarded REAL-mode path internally inconsistent. The API now consumes the one-time authorization immediately before the guarded mode transition and fails closed if consumption fails.

## Safety result
No new REAL capability was enabled. The change closes an authorization-path inconsistency while preserving explicit human arming, one-shot consumption, preflight, reconciliation, readiness and execution-gate controls.

## Validation
- Focused SAFE_MODE recovery tests: 7 passed (tests/test_account_reconciliation.py -k recovery).
- py_compile and git diff --check: to be rerun after this checkpoint.
- Full account-reconciliation pytest remains known to stall in the Windows environment; no green claim is made for the full suite.
