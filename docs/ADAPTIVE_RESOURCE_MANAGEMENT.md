# Adaptive runtime resource management

The adaptive resource manager samples CPU count, total/available memory, free
disk space, operating system and current CPU load. It derives a bounded compute
policy and can be refreshed after startup, installation/upgrade, hardware
changes or runtime load changes.

Profiles are computed, not fixed product tiers:

- **COMPACT**: preserve core public market-data collection, observational radar,
  PAPER bookkeeping, persistence and health telemetry. Set backtest,
  simulation and analysis worker budgets to zero; defer optional historical
  studies and other heavy work until the host has sufficient headroom.
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

## Runtime scheduler integration

The engine creates one adaptive resource manager from the installed runtime configuration and passes it to the research inbox worker. The worker refreshes the policy at the configured interval. COMPACT policy defers optional external research/evaluation work while the core engine loop, public market-data collector, observational radar, PAPER state, persistence and health telemetry continue independently. BALANCED/PERFORMANCE policies bound the sequential inbox batch size using the analysis and general worker budgets (maximum four requests per loop). If resource sampling fails, optional research is deferred rather than running without a trustworthy budget.

The resource policy is exposed in research-worker supervision telemetry. This integration does not interrupt an item already being processed, terminate applications, change trading permissions, or affect risk limits. Other heavy-job entrypoints (backtests and simulations) remain separate integration work and must consume their own budgets before being considered resource-managed.
