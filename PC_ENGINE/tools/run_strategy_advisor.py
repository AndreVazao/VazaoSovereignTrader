from __future__ import annotations

import argparse
import json
from pathlib import Path

from PC_ENGINE.research.strategy_advisor import assess_strategy_report, write_advisor_report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create conservative PAPER-only strategy research guidance from a study report."
    )
    parser.add_argument("--study", default="PC_ENGINE/data/radar/paper_study_report.json")
    parser.add_argument("--output", default="PC_ENGINE/data/radar/strategy_advisor_report.json")
    parser.add_argument("--min-outcomes", type=int, default=100)
    parser.add_argument("--min-oos-samples", type=int, default=30)
    parser.add_argument("--min-regime-samples", type=int, default=20)
    parser.add_argument("--min-positive-fold-ratio", type=float, default=0.60)
    parser.add_argument("--max-probability-non-positive", type=float, default=0.25)
    args = parser.parse_args()

    study_path = Path(args.study)
    if not study_path.is_file():
        raise SystemExit(f"Study report not found: {study_path}")
    try:
        study = json.loads(study_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Study report is unreadable: {type(exc).__name__}") from exc
    if not isinstance(study, dict):
        raise SystemExit("Study report must contain a JSON object")

    result = assess_strategy_report(
        study,
        min_outcomes=args.min_outcomes,
        min_oos_samples=args.min_oos_samples,
        min_regime_samples=args.min_regime_samples,
        min_positive_fold_ratio=args.min_positive_fold_ratio,
        max_probability_non_positive=args.max_probability_non_positive,
    )
    write_advisor_report(result, args.output)
    print(f"Decision: {result['decision']}")
    print(f"Rationale: {result['rationale']}")
    print(f"Report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
