from __future__ import annotations

import argparse

from PC_ENGINE.radar.l2_oos_validation import L2OutOfSampleValidator


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate executable L2 replay out-of-sample in PAPER mode.")
    parser.add_argument("--input", default="PC_ENGINE/data/replay/l2_temporal_replay.json")
    parser.add_argument("--output", default="PC_ENGINE/data/radar/l2_oos_validation.json")
    parser.add_argument("--min-in", type=int, default=30)
    parser.add_argument("--min-out", type=int, default=20)
    parser.add_argument("--min-completion", type=float, default=0.55)
    args = parser.parse_args()

    rows = L2OutOfSampleValidator(
        replay_path=args.input,
        output_path=args.output,
        min_in_samples=args.min_in,
        min_out_samples=args.min_out,
        min_completion_rate=args.min_completion,
    ).validate()
    print(f"Validated L2 relationships: {len(rows)} | stable: {sum(r.stable for r in rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
