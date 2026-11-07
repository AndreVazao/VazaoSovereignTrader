from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from PC_ENGINE.replay.microstructure_replay import MicrostructureReplay, MicrostructureReplayConfig
from PC_ENGINE.core.adaptive_job_runner import run_adaptive_simulation, AdaptiveJobDeferred


def main() -> int:
    parser = argparse.ArgumentParser(description="Run conservative PAPER microstructure replay.")
    parser.add_argument("--input", default="PC_ENGINE/data/radar/websocket_events.jsonl")
    parser.add_argument("--output", default="PC_ENGINE/data/replay/microstructure_replay.json")
    parser.add_argument("--capital", type=float, default=100.0)
    parser.add_argument("--latency-ms", type=float, default=80.0)
    parser.add_argument("--holding-ms", type=float, default=1000.0)
    args = parser.parse_args()
    try:
        report = run_adaptive_simulation(lambda: MicrostructureReplay(MicrostructureReplayConfig(
            input_path=args.input,
            output_path=args.output,
            capital_per_trade=args.capital,
            latency_ms=args.latency_ms,
            holding_ms=args.holding_ms,
        )).run())
    except AdaptiveJobDeferred as exc:
        raise SystemExit(f"Microstructure replay deferred safely: {exc}") from exc
    print(json.dumps(asdict(report), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
