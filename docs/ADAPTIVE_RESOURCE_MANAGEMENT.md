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
Missing measurements fail conservatively. The engine refreshes the manager at
the configured interval for the research worker; CLI heavy-job gates refresh
the policy before each new admission.

## Runtime scheduler integration

The engine creates one adaptive resource manager from the installed runtime
configuration and passes it to the research inbox worker. The worker refreshes
the policy at the configured interval. COMPACT policy defers optional external
research/evaluation work while the core engine loop, public market-data
collector, observational radar, PAPER state, persistence and health telemetry
continue independently. BALANCED/PERFORMANCE policies bound the sequential
inbox batch size using the analysis and general worker budgets (maximum four
requests per loop). If resource sampling fails, optional research is deferred
rather than running without a trustworthy budget.

## Cross-process heavy-job admission

Backtests, offline PAPER studies, walk-forward/replay and analysis entrypoints
use `AdaptiveJobGate` before starting optional compute-heavy work. The gate
refreshes the current policy and acquires an operating-system file-lock slot
under `DATA_DIR/.runtime/resource-leases`. A short admission lock serializes
slot selection across processes; the selected slot remains locked until the
job exits. The operating system releases the lock if its process crashes, so
stale lease records do not accumulate.

A zero budget, failed resource probe, unavailable lease directory or lock
failure defers new work. A refreshed policy affects new admissions only; it
does not terminate an active job. The gate applies only to VST entrypoints that
use it. It does not constrain arbitrary external processes, provide CPU/memory
sandbox quotas or authorize trading. All these workloads remain PAPER/research
only and cannot change risk or execution permissions.
