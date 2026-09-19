from __future__ import annotations

import argparse
import json

from PC_ENGINE.replay.l2_temporal import L2TemporalConfig, L2TemporalExecutableReplay


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay lead/lag against reconstructed L2 depth in PAPER mode.")
    parser.add_argument("--input", default=L2TemporalConfig.input_path)
    parser.add_argument("--output", default=L2TemporalConfig.output_path)
    parser.add_argument("--capital", type=float, default=L2TemporalConfig.capital_per_trade)
    parser.add_argument("--fee-bps", type=float, default=L2TemporalConfig.fee_bps)
    parser.add_argument("--latency-ms", type=float, default=L2TemporalConfig.latency_ms)
    parser.add_argument("--holding-ms", type=float, default=L2TemporalConfig.holding_ms)
    parser.add_argument("--max-impact-bps", type=float, default=L2TemporalConfig.max_execution_impact_bps)
    args = parser.parse_args()

    config = L2TemporalConfig(
        input_path=args.input,
        output_path=args.output,
        capital_per_trade=args.capital,
        fee_bps=args.fee_bps,
        latency_ms=args.latency_ms,
        holding_ms=args.holding_ms,
        max_execution_impact_bps=args.max_impact_bps,
    )
    print(json.dumps(L2TemporalExecutableReplay(config).run().__dict__, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
