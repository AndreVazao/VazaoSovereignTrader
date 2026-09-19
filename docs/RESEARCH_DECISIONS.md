# Research Decisions

## Adopted

### 1. First-order market data for fast decisions
Use WebSocket trades/order-book data for latency-sensitive detection. Keep REST/CCXT OHLCV for slower analysis, reconciliation and recovery.

### 2. Cost-aware validation
All learned expectancy must be evaluated net of a cost floor. The PAPER broker continues to model fee, slippage and rejection.

### 3. Walk-forward discipline
Do not promote a strategy because of one optimized backtest. Future validation should use chronological windows, a final untouched holdout and explicit tracking of how many variants were tested.

### 4. Bounded learning influence
Historical learning is an input to opportunity ranking, never a replacement for Risk Engine controls.

### 5. No latency arms race
The project should optimize end-to-end decision latency and data freshness, not attempt exchange-HFT microsecond competition from a consumer PC.

## Not adopted

- Unbounded reinforcement learning controlling orders.
- Blind parameter optimization against the same dataset used for validation.
- Disabling exchange rate limits.
- Browser automation as a primary execution mechanism.
- Futures/leverage/withdrawal automation in the initial production path.
