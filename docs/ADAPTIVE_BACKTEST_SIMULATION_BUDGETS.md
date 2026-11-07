# Adaptive backtest and simulation budgets

Backtest and offline PAPER-study entrypoints request an admission slot before
starting compute-heavy work.

- Backtests use max_backtest_workers.
- Historical PAPER studies, walk-forward analysis and Monte Carlo use
  max_simulation_workers.
- A zero budget defers new work without starting it.
- Failed resource sampling fails closed and defers new work.
- A refreshed policy controls new admission only; running jobs are not killed
  or interrupted when host capacity drops.
- CLI entrypoints load the backend adaptive resource configuration.
- These gates do not submit orders and cannot change PAPER/REAL permissions,
  risk limits, Market Data, Radar, or persistence priority.

The current commands run one job per process. The gate also enforces concurrent
admission when multiple jobs are invoked inside one process.
