# Hot Path Lead/Lag Hardening — 2026-10-10

## Scope
Harden the local, observation-only lead/lag detector in `PC_ENGINE/radar/hot_path.py`. No strategy thresholds were relaxed and no execution capability was added.

## Changes
- Canonicalize configured venue IDs and incoming exchange/symbol IDs before indexing quotes and learned expectancy.
- Reject unknown venues, empty symbols, non-positive/non-finite prices, non-positive timestamps, and invalid/negative receive-latency measurements.
- Reject non-finite learned expectancy values rather than allowing invalid floating-point values into the hot path.
- Calculate local quote age without clamping negative values to zero. A follower quote received after the leader observation is inconsistent with a lagging-venue signal and is rejected.
- Preserve the invariant that every emitted opportunity remains `paper_only=true` and `execution_allowed=false`.

## Regression coverage
Four tests were added for future follower timestamps, case/whitespace normalization, invalid prices, and non-finite expectancy.

## Validation
- Focused lead/lag suite: 29 passed.
- Broader brain/learning suite across GOD Ultra, market state, WebSocket radar, lead/lag, hot path, outcomes, learning, champion/challenger, state outcomes, regime and walk-forward: 61 passed in 18.91s.
- No trading engine was started; no orders or exchange-side effects were performed.

## Remaining
- Android 16 native Kivy/HWUI crash remains a separate unresolved blocker.
- PowerShell USB/token bootstrap scripts remain unmodified because the earlier remote edit attempts were blocked; revisit separately.
- This hardening is local to the current branch and is not claimed merged into main.

## Follow-up hardening — 2026-10-11

- `set_expectancies()` now validates and normalizes the entire batch before taking the lock and applying one atomic update. Invalid values or empty identity fields leave the previous model unchanged.
- `HotPathOutcomeTracker.on_market_event()` now rejects malformed/non-positive timestamps and non-finite/non-positive prices before examining pending outcomes. Venue/symbol identifiers are normalized consistently, and invalid quotes do not consume pending observations.
- Added regressions for atomic batch rejection, empty identities, NaN prices, invalid timestamps, and normalized outcome-event identity.
- Validation: **65 tests passed in 7.85s** across hot path, outcome tracking, calibration, OOS robustness, lead/lag learning, evidence learning, champion outcomes/runtime, state outcomes, regime, walk-forward, GOD Ultra, market state, WebSocket radar and lead/lag validation. `compileall` and `git diff --check` passed.
- Still observation-only/PAPER; no engine startup, exchange calls, orders, paid inference, or REAL-mode changes.

## Follow-up hardening — 2026-10-11 (outcome registration)

- `HotPathOutcomeTracker.register()` now validates opportunity identity, direction, positive horizon/timestamps/prices, finite signal and price values, non-negative cost components, and consistency of expected net edge with gross expectation minus fees/slippage/latency penalty.
- Accepted identity fields are canonicalized before entering the pending queue; malformed/inconsistent records are rejected before they can pollute calibration evidence.
- Added regressions for NaN/infinite evidence, negative costs, inconsistent expected-net values, and identity normalization at registration.
- Selected brain/learning suite: **67 passed in 7.47s**; `compileall` and `git diff --check` passed.
- Remains bounded, in-memory, PAPER-only and order-free.
