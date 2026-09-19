# Real-Time Lead/Lag Engine

The engine consumes normalized WebSocket market events and looks for a
directional move at one venue followed by the same directional move at another
venue within a configured time window.

## Evidence chain

1. Prefer exchange event timestamp.
2. Otherwise use provider timestamp.
3. Otherwise use calibrated local wall-clock receive time.
4. Preserve event IDs so every signal is replayable.

The detector requires a minimum movement in basis points and a positive lag.
It emits an observational LeadLagSignal; it does not execute trades.

## Important limitation

A single observed lead/follower pair is a hypothesis, not proof of a durable
market advantage. The signal must feed historical aggregation, out-of-sample
validation, cost modelling and risk gates before any execution intent exists.

## Next phase

Aggregate signals by venue pair, symbol and direction; measure frequency,
median/p95/p99 lag, directional consistency and post-signal executable return.
