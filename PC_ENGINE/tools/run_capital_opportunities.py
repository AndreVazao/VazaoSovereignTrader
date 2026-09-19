from __future__ import annotations

import argparse
import json

from PC_ENGINE.opportunity.capital_opportunity import CapitalOpportunityEngine


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyse persisted radar events for capital-efficient opportunities"
    )
    parser.add_argument("--observations", default="PC_ENGINE/data/radar/observations.jsonl")
    parser.add_argument("--output", default="PC_ENGINE/data/radar/capital_opportunities.jsonl")
    parser.add_argument("--min-samples", type=int, default=30)
    parser.add_argument("--max-lag-ms", type=int, default=2000)
    parser.add_argument("--min-net-edge-bps", type=float, default=2.0)
    parser.add_argument("--fee-bps", type=float, default=10.0)
    parser.add_argument("--spread-bps", type=float, default=4.0)
    parser.add_argument("--slippage-bps", type=float, default=5.0)
    parser.add_argument("--latency-buffer-bps", type=float, default=3.0)
    parser.add_argument("--capital", type=float, default=100.0)
    args = parser.parse_args()

    engine = CapitalOpportunityEngine(
        observations_path=args.observations,
        output_path=args.output,
        min_samples=args.min_samples,
        max_lag_ms=args.max_lag_ms,
        min_net_edge_bps=args.min_net_edge_bps,
        fee_bps=args.fee_bps,
        spread_bps=args.spread_bps,
        slippage_bps=args.slippage_bps,
        latency_buffer_bps=args.latency_buffer_bps,
        default_required_capital=args.capital,
    )
    candidates = engine.analyze()
    print(json.dumps([candidate.__dict__ for candidate in candidates], ensure_ascii=False))


if __name__ == "__main__":
    main()
