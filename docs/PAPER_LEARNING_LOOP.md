# PAPER Learning Loop

The trader now has a closed PAPER research loop:

1. Public market observations are collected by the existing PAPER collector.
2. Market states are stored in `PC_ENGINE/data/radar/market_states.jsonl`.
3. State-signature learning evaluates future outcomes net of a conservative cost floor.
4. Eligible signatures are written to `state_signature_learning.jsonl`.
5. `PaperOpportunityEngine` reads those learned signatures as bounded advisory evidence.
6. Capital allocation still occurs only after the existing Risk Engine checks.
7. Every closed PAPER trade feeds the existing ledger/outcome history.

## Important separation

Learning cannot place an order, change risk limits, authorize REAL mode, or bypass the Order Manager.

The intended evolution is:

`market data -> market state -> learning -> opportunity ranking -> allocator -> risk -> paper execution -> outcome -> learning`

## Why this approach

Recent research and practitioner documentation reinforce three points relevant to this project:

- realistic transaction costs matter;
- walk-forward/out-of-sample validation is preferable to tuning on the same data used for evaluation;
- low-latency paths should use first-order trades/order-book data instead of repeatedly polling slower derived candles where timing matters.

The implementation therefore keeps learning conservative and uses the existing WebSocket radar for future fast-path work instead of making REST polling the execution trigger.
