from __future__ import annotations

import argparse
import json

from PC_ENGINE.core.walk_forward import WalkForwardEvaluator
from PC_ENGINE.core.adaptive_job_runner import run_adaptive_simulation, AdaptiveJobDeferred


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate PAPER confluence with chronological walk-forward validation")
    parser.add_argument("--data-dir", default="PC_ENGINE/data/radar")
    parser.add_argument("--train-fraction", type=float, default=0.70)
    parser.add_argument("--min-train", type=int, default=50)
    parser.add_argument("--min-validation", type=int, default=30)
    parser.add_argument("--min-mean-bps", type=float, default=0.0)
    parser.add_argument("--min-win-rate", type=float, default=0.50)
    args = parser.parse_args()

    evaluator = WalkForwardEvaluator(
        data_dir=args.data_dir,
        train_fraction=args.train_fraction,
        min_train_samples=args.min_train,
        min_validation_samples=args.min_validation,
        min_validation_mean_bps=args.min_mean_bps,
        min_validation_win_rate=args.min_win_rate,
    )
    try:
        report = run_adaptive_simulation(evaluator.evaluate)
    except AdaptiveJobDeferred as exc:
        raise SystemExit(f"Walk-forward validation deferred safely: {exc}") from exc
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
