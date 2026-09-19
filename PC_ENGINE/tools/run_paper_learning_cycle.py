from __future__ import annotations

import argparse
import json

from PC_ENGINE.learning.state_signature import StateSignatureLearningEngine
from PC_ENGINE.radar.market_state import MarketStateStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild PAPER state-signature learning.")
    parser.add_argument("--limit", type=int, default=20000)
    parser.add_argument("--cost-bps", type=float, default=28.0)
    parser.add_argument("--min-samples", type=int, default=30)
    args = parser.parse_args()

    states = MarketStateStore().recent(limit=max(1, args.limit))
    learner = StateSignatureLearningEngine(
        cost_bps=args.cost_bps,
        min_samples=args.min_samples,
    )
    stats = learner.evaluate(states)

    path = learner_output_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in stats:
            handle.write(json.dumps(row.__dict__, separators=(",", ":"), sort_keys=True) + "\n")

    print(json.dumps({
        "states": len(states),
        "signatures": len(stats),
        "eligible": sum(row.eligible for row in stats),
        "output": str(path),
    }, indent=2))


def learner_output_path():
    from pathlib import Path
    return Path("PC_ENGINE/data/radar/state_signature_learning.jsonl")


if __name__ == "__main__":
    main()
