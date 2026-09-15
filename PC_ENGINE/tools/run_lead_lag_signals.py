from __future__ import annotations

import argparse
import json
from PC_ENGINE.radar.lead_lag_signal import LeadLagSignalEngine


def main() -> None:
    parser = argparse.ArgumentParser(description="Show learned lead/lag opportunities in PAPER only")
    parser.add_argument("--min-confidence", type=float, default=0.75)
    args = parser.parse_args()
    engine = LeadLagSignalEngine()
    signals = engine.signals(min_confidence=args.min_confidence)
    print(json.dumps({"paper_only": True, "signals": [s.__dict__ for s in signals]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
