# Adaptive runtime resource management

The adaptive resource manager samples CPU count, total/available memory, free
disk space, operating system and current CPU load. It derives a bounded compute
policy and can be refreshed after startup, installation/upgrade, hardware
changes or runtime load changes.

Profiles are computed, not fixed product tiers:

- **COMPACT**: preserve core public market-data collection, observational radar,
  PAPER bookkeeping, persistence and health telemetry; defer backtests,
  simulations and parallel analysis when headroom is constrained.
- **BALANCED**: permit modest bounded analysis and one backtest/simulation worker.
- **PERFORMANCE**: scale research concurrency on machines with substantial
  CPU and memory headroom.

The manager is a policy provider; callers must apply its worker budgets at
their scheduling boundaries. It does not terminate applications or processes.
It never changes trading mode, REAL permission, risk thresholds or promotion
permissions. Resource headroom is not trading authorization.

The sampler uses optional psutil when available and standard-library fallbacks.
Missing measurements fail conservatively. The manager can be refreshed at any
time; a future runtime integration should call refresh periodically and before
starting heavy jobs.
