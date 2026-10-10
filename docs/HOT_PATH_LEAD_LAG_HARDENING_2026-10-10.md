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
