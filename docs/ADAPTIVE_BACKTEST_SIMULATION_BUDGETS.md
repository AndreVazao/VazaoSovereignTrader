# Adaptive backtest and simulation budgets

Backtest and offline PAPER-study entrypoints request an admission slot before
starting compute-heavy work.

- Backtests use `max_backtest_workers`.
- Historical PAPER studies, walk-forward analysis and Monte Carlo use
  `max_simulation_workers`.
- A zero budget defers new work without starting it.
- Failed resource sampling fails closed and defers new work.
- A refreshed policy controls new admission only; running jobs are not killed
  or interrupted when host capacity drops.
- CLI entrypoints load the backend adaptive resource configuration.
- These gates do not submit orders and cannot change PAPER/REAL permissions,
  risk limits, Market Data, Radar or persistence priority.

The gate coordinates separate VST processes through OS-backed lock slots under
`DATA_DIR/.runtime/resource-leases`. A short-lived admission lock makes slot
selection atomic; the selected slot stays locked for the job lifetime and is
released automatically by the operating system if the process exits
unexpectedly. The gate refreshes policy before each admission and fails closed
when the lease store cannot be used.

This protects only the backtest, simulation and analysis entrypoints that use
the gate. It does not limit unrelated processes or terminate a running job
after the host becomes constrained.
