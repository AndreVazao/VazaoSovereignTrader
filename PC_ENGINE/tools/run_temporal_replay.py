from __future__ import annotations

import argparse
import json

from PC_ENGINE.replay.temporal import ReplayConfig, TemporalWebSocketReplay


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic PAPER replay of collected WebSocket events.")
    parser.add_argument("--input", default="PC_ENGINE/data/radar/websocket_events.jsonl")
    parser.add_argument("--output", default="PC_ENGINE/data/replay/temporal_replay.json")
    parser.add_argument("--capital", type=float, default=100.0)
    parser.add_argument("--holding-ms", type=float, default=1000.0)
    parser.add_argument("--latency-ms", type=float, default=80.0)
    args = parser.parse_args()
    report = TemporalWebSocketReplay(ReplayConfig(
        input_path=args.input,
        output_path=args.output,
        capital_per_trade=args.capital,
        holding_ms=args.holding_ms,
        latency_ms=args.latency_ms,
    )).run()
    print(json.dumps(report.__dict__, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
