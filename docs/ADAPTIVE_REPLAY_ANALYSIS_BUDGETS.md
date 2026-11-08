# Adaptive replay and analysis budgets

The shared run_adaptive_simulation boundary applies the
max_simulation_workers policy to offline, compute-heavy PAPER replay and
simulation entrypoints:

- WebSocket temporal replay
- Microstructure replay
- L2 microstructure replay
- L2 temporal replay
- Walk-forward evaluation
- L2 out-of-sample validation
- PAPER statistical study

The run_adaptive_analysis boundary applies the separate
max_analysis_workers policy to offline PAPER analysis entrypoints:

- Standalone regime validation
- Standalone lead/lag out-of-sample validation
- The combined readiness analysis pipeline (state outcomes, walk-forward and
  regime evaluation)

A zero budget, failed resource probe, or unavailable adaptive configuration
defers the job before its compute stage starts. The command reports an explicit
safe deferral instead of silently running without a policy. Jobs already in
progress are not interrupted. The readiness pipeline does not overwrite its
previous reports when the analysis is deferred.

An explicit adaptive_resources.enabled = false remains an operator override.
The gate does not submit orders, change risk limits, or alter PAPER/REAL
permissions. Continuous Market Data collection, Radar observation, and PAPER
persistence remain outside this optional-analysis gate.
