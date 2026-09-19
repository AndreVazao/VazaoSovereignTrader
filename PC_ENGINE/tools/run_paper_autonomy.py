from __future__ import annotations

import argparse
import json

from PC_ENGINE.autonomy.paper_orchestrator import PaperAutonomyOrchestrator


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate GOD Ultra PAPER intents from validated L2 evidence.")
    parser.add_argument("--validation", default="PC_ENGINE/data/radar/l2_oos_validation.json")
    parser.add_argument("--replay", default="PC_ENGINE/data/replay/l2_temporal_replay.json")
    parser.add_argument("--output", default="PC_ENGINE/data/paper/autonomous_intents.jsonl")
    parser.add_argument("--capital", type=float, default=1000.0)
    parser.add_argument("--exposure", type=float, default=0.0)
    parser.add_argument("--max-exposure", type=float, default=350.0)
    args = parser.parse_args()
    rows = PaperAutonomyOrchestrator(
        validation_path=args.validation,
        replay_path=args.replay,
        output_path=args.output,
    ).run(
        available_capital=args.capital,
        current_exposure=args.exposure,
        max_exposure=args.max_exposure,
    )
    print(json.dumps({"paper_intents": rows}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
