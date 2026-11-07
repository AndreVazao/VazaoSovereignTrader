# Adaptive budget for collector-side PAPER studies

The continuous public WebSocket market-data collector, Radar event callback,
PAPER outcome buffering/persistence, and health heartbeat remain active
independently of optional offline study work.

The periodic PAPER study now enters the shared adaptive simulation gate before
loading its historical state file. This is intentional: reading up to the
configured state limit can itself consume significant memory, before Monte
Carlo and walk-forward calculations begin.

When the resource profile has no simulation capacity, or resource/configuration
sampling fails, the study is recorded in collector health as
`DEFERRED_RESOURCE_BUDGET` and retried at the next configured study interval.
The collector does not stop, and incoming public market data and PAPER outcome
persistence continue. An admitted study retains its existing configured
parameters and outputs.

This gate changes compute scheduling only. It does not change trading mode,
order permissions, risk limits, or data-retention behavior.
