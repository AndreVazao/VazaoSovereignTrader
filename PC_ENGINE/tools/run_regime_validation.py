from __future__ import annotations

import argparse
import json

from PC_ENGINE.core.adaptive_job_gate import AdaptiveJobDeferred
from PC_ENGINE.core.adaptive_job_runner import run_adaptive_analysis
from PC_ENGINE.core.regime_validation import RegimeAwareValidator


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate PAPER confluence by market regime")
    parser.add_argument("--data-dir", default="PC_ENGINE/data/radar")
    parser.add_argument("--min-samples", type=int, default=30)
    parser.add_argument("--min-mean-bps", type=float, default=0.0)
    parser.add_argument("--min-win-rate", type=float, default=0.50)
    args = parser.parse_args()
    validator = RegimeAwareValidator(
        data_dir=args.data_dir,
        min_samples=args.min_samples,
        min_mean_net_bps=args.min_mean_bps,
        min_win_rate=args.min_win_rate,
    )
    try:
        result = run_adaptive_analysis(validator.evaluate)
    except AdaptiveJobDeferred as exc:
        raise SystemExit(f"Regime validation deferred safely: {exc}") from exc
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
