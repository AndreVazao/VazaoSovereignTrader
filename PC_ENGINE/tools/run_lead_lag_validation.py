from __future__ import annotations

import argparse

from PC_ENGINE.core.adaptive_job_gate import AdaptiveJobDeferred
from PC_ENGINE.core.adaptive_job_runner import run_adaptive_analysis
from PC_ENGINE.radar.lead_lag_validation import LeadLagValidationEngine


def main() -> None:
    parser = argparse.ArgumentParser(description="Run PAPER out-of-sample lead/lag validation")
    parser.add_argument("--data-dir", default="PC_ENGINE/data/radar")
    parser.add_argument("--horizon-ms", type=int, default=1000)
    parser.add_argument("--min-in", type=int, default=50)
    parser.add_argument("--min-out", type=int, default=30)
    parser.add_argument("--cost-bps", type=float, default=28.0)
    args = parser.parse_args()
    try:
        rows = run_adaptive_analysis(
            lambda: LeadLagValidationEngine(
                args.data_dir,
                min_in_samples=args.min_in,
                min_out_samples=args.min_out,
                cost_bps=args.cost_bps,
            ).validate(args.horizon_ms)
        )
    except AdaptiveJobDeferred as exc:
        raise SystemExit(f"Lead/lag validation deferred safely: {exc}") from exc
    print(f"Validated relationships: {len(rows)} | stable: {sum(row.stable for row in rows)}")
    for row in rows[:10]:
        print(
            f"{row.leader}->{row.follower} {row.symbol} {row.direction} "
            f"OUT={row.out_expectancy_bps:.2f}bps stable={row.stable}"
        )


if __name__ == "__main__":
    main()
