from __future__ import annotations

import argparse
import json
from PC_ENGINE.radar.lead_lag_learning import LeadLagLearningEngine


def main() -> None:
    p = argparse.ArgumentParser(description="Build the PAPER-only Sovereign lead/lag learning report")
    p.add_argument("--min-samples", type=int, default=100)
    p.add_argument("--fee-bps", type=float, default=10.0)
    p.add_argument("--slippage-bps", type=float, default=4.0)
    p.add_argument("--response-bps", type=float, default=2.0)
    p.add_argument("--horizons-ms", default="100,250,500,1000,2000,5000")
    args = p.parse_args()
    horizons = tuple(int(x.strip()) for x in args.horizons_ms.split(",") if x.strip())
    engine = LeadLagLearningEngine(min_samples=args.min_samples, fee_bps_per_side=args.fee_bps,
                                   slippage_bps_per_side=args.slippage_bps,
                                   response_threshold_bps=args.response_bps)
    stats = engine.learn(horizons)
    print(json.dumps({"paper_only": True, "stats": [s.__dict__ for s in stats],
                      "eligible_signals": engine.eligible_signals(stats)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
