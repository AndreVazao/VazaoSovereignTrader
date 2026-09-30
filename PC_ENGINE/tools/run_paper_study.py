from __future__ import annotations

import argparse

from PC_ENGINE.research.paper_study import load_states, run_study, write_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a PAPER-only statistical study over local market states.")
    parser.add_argument("--states", default="PC_ENGINE/data/radar/market_states.jsonl")
    parser.add_argument("--output", default="PC_ENGINE/data/radar/paper_study_report.json")
    parser.add_argument("--horizon-ms", type=int, default=5000)
    parser.add_argument("--cost-bps", type=float, default=28.0)
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--min-train", type=int, default=100)
    parser.add_argument("--test-size", type=int, default=50)
    parser.add_argument("--monte-carlo-iterations", type=int, default=2000)
    args = parser.parse_args()

    states = load_states(args.states)
    report = run_study(
        states,
        horizon_ms=args.horizon_ms,
        cost_bps=args.cost_bps,
        folds=args.folds,
        min_train=args.min_train,
        test_size=args.test_size,
        monte_carlo_iterations=args.monte_carlo_iterations,
    )
    write_report(report, args.output)
    print(f"PAPER study complete: {len(states)} states -> {args.output}")
    print(f"Outcomes: {report['outcome_samples']} | mean net bps: {report['overall']['mean_net_bps']:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
