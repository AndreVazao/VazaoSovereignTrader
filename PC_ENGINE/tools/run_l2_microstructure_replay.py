from __future__ import annotations

import argparse
import json

from PC_ENGINE.replay.l2_microstructure import L2MicrostructureReplay


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay reconstructed L2 books in PAPER mode.")
    parser.add_argument("--input", default="PC_ENGINE/data/radar/websocket_orderbook_events.jsonl")
    parser.add_argument("--output", default="PC_ENGINE/data/replay/l2_microstructure.json")
    parser.add_argument("--notional", type=float, default=100.0)
    args = parser.parse_args()

    report = L2MicrostructureReplay(
        input_path=args.input,
        output_path=args.output,
        notional_per_side=args.notional,
    ).run()
    print(json.dumps(report.__dict__, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
