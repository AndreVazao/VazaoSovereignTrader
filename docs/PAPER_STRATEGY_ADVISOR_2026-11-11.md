# PAPER Strategy Advisor — 2026-11-11

## Purpose

The Strategy Advisor converts the existing statistical PAPER study into a small,
auditable research decision. It does not invent a profitable strategy, change
strategy parameters, promote a candidate, change risk, authorize REAL, or submit
orders.

## Data flow

1. Run the existing PAPER study over persisted market states:
   `python -m PC_ENGINE.tools.run_paper_study`
2. Assess its report:
   `python -m PC_ENGINE.tools.run_strategy_advisor`
3. Inspect
   `PC_ENGINE/data/radar/strategy_advisor_report.json` and
   `PC_ENGINE/data/radar/strategy_discovery_report.json`.

The command also runs `PC_ENGINE.research.strategy_discovery` under the adaptive simulation resource gate. It searches a small, deterministic grid of confidence/confluence filters on a purged training window, selects one candidate using training results only, and evaluates that candidate once on the untouched chronological OOS window. It records a baseline OOS result and an OOS-only bootstrap. The candidate is a research hypothesis; its parameters are never applied to runtime.

The advisor consumes the report produced by `PC_ENGINE.research.paper_study`. The Monte Carlo gate uses the dedicated `monte_carlo_oos` result, never the full-sample bootstrap. Chronological and walk-forward training windows purge any outcome whose forward label crosses the test boundary.
Missing, malformed, non-PAPER, or inadequate evidence is never interpreted as
success.

## Default decision gates

- At least 100 resolved outcomes.
- At least 30 chronological out-of-sample outcomes.
- Positive net expectancy in the OOS test after the study's configured costs.
- At least 60% of available walk-forward test folds with positive mean net bps.
- OOS-only Monte Carlo bootstrap probability of non-positive mean no greater than 25%.
- Forward outcome labels that overlap a chronological test boundary are purged from training.
- At least one regime with 20 or more observations.
- Discovery candidate thresholds are selected on training data only; forward labels crossing the OOS boundary are purged using the actual timestamp of the future market observation that resolves each label (not merely the requested horizon timestamp).

Decisions:

- `INSUFFICIENT_EVIDENCE`: sample or walk-forward evidence is too small.
- `CONTINUE_PAPER_RESEARCH`: all gates pass; this means further PAPER research,
  not deployment or promotion.
- `REJECT_OR_REWORK`: one or more statistical gates fail.

Thresholds are configurable from the CLI. They are conservative operational
defaults, not universal statistical guarantees. The report preserves each gate,
metric, regime sample count, and safety invariant.

## Safety

The advisor is a pure research function. It has no broker, exchange, credential,
risk-manager, order, or REAL-mode dependency. It writes an atomic JSON report.
No evidence, no recommendation. A positive report is not proof of future returns
and does not authorize capital.

## Release validation still required

Run the full Python suite and inspect the exact commit's CI. Validate the study
against real persisted market data on the Windows host before treating any
strategy finding as operational evidence. The existing low-memory PC should run
the study under the adaptive resource gate and with bounded sample/Monte Carlo
settings.
