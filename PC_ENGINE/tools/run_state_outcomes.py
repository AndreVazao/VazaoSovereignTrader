from __future__ import annotations

import argparse
import json
from pathlib import Path

from PC_ENGINE.radar.state_outcomes import StateOutcomeEngine


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate PAPER MarketState outcomes")
    parser.add_argument("--input", default="PC_ENGINE/data/radar/market_states.jsonl")
    parser.add_argument("--output", default="PC_ENGINE/data/radar/state_outcomes.jsonl")
    parser.add_argument("--cost-bps", type=float, default=28.0)
    args = parser.parse_args()

    path = Path(args.input)
    if not path.exists():
        raise SystemExit(f"MarketState file not found: {path}")
    states = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            states.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    engine = StateOutcomeEngine(cost_bps=args.cost_bps)
    stats = engine.evaluate(states)
    engine.save(stats, args.output)
    print(json.dumps({"states": len(states), "stats": len(stats), "output": args.output}, indent=2))


if __name__ == "__main__":
    main()
