from __future__ import annotations

import argparse
from PC_ENGINE.core.config import DATA_DIR, load_config
from PC_ENGINE.core.adaptive_resource_manager import AdaptiveResourceManager
from PC_ENGINE.core.adaptive_job_gate import AdaptiveJobDeferred, AdaptiveJobGate

from PC_ENGINE.research.paper_study import load_states, run_study, write_report
from PC_ENGINE.research.strategy_advisor import assess_strategy_report, write_advisor_report
from PC_ENGINE.research.strategy_discovery import discover_strategy


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a PAPER-only statistical study and strategy research assessment.")
    parser.add_argument("--states", default="PC_ENGINE/data/radar/market_states.jsonl")
    parser.add_argument("--output", default="PC_ENGINE/data/radar/paper_study_report.json")
    parser.add_argument("--advisor-output", default="PC_ENGINE/data/radar/strategy_advisor_report.json")
    parser.add_argument("--discovery-output", default="PC_ENGINE/data/radar/strategy_discovery_report.json")
    parser.add_argument("--horizon-ms", type=int, default=5000)
    parser.add_argument("--cost-bps", type=float, default=28.0)
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--min-train", type=int, default=100)
    parser.add_argument("--test-size", type=int, default=50)
    parser.add_argument("--monte-carlo-iterations", type=int, default=2000)
    args = parser.parse_args()

    states = load_states(args.states)
    config = load_config()
    adaptive_cfg = dict(config.get("adaptive_resources", {}))
    resource_manager = None
    if bool(adaptive_cfg.get("enabled", True)):
        resource_manager = AdaptiveResourceManager(root=DATA_DIR, reserve_memory_mb=int(adaptive_cfg.get("reserve_memory_mb", 512)), max_workers_cap=adaptive_cfg.get("max_workers_cap"))
    try:
        report = run_study(
            states,
            horizon_ms=args.horizon_ms,
            cost_bps=args.cost_bps,
            folds=args.folds,
            min_train=args.min_train,
            test_size=args.test_size,
            monte_carlo_iterations=args.monte_carlo_iterations,
            resource_manager=resource_manager,
        )
    except AdaptiveJobDeferred as exc:
        raise SystemExit(f"PAPER study deferred safely: {exc}") from exc
    write_report(report, args.output)
    advisor = assess_strategy_report(report)
    write_advisor_report(advisor, args.advisor_output)
    if resource_manager is None:
        discovery = discover_strategy(
            states, horizon_ms=args.horizon_ms, cost_bps=args.cost_bps,
            monte_carlo_iterations=args.monte_carlo_iterations,
        )
    else:
        with AdaptiveJobGate(resource_manager).slot("simulation") as admitted:
            discovery = discover_strategy(
                states, horizon_ms=args.horizon_ms, cost_bps=args.cost_bps,
                monte_carlo_iterations=args.monte_carlo_iterations,
            ) if admitted else {
                "schema_version": 1, "status": "DEFERRED_RESOURCE_GUARD",
                "paper_only": True, "orders_submitted": False,
            }
    write_report(discovery, args.discovery_output)
    print(f"PAPER study complete: {len(states)} states -> {args.output}")
    print(f"Outcomes: {report['outcome_samples']} | mean net bps: {report['overall']['mean_net_bps']:.4f}")
    print(f"Strategy advisor: {advisor['decision']} -> {args.advisor_output}")
    print(f"Strategy discovery: {discovery['status']} -> {args.discovery_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
