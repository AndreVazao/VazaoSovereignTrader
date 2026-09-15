from __future__ import annotations

import argparse
import json

from PC_ENGINE.core.real_readiness import RealReadinessGate


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate protected REAL readiness")
    parser.add_argument("--mode", default="PAPER")
    parser.add_argument("--state-samples", type=int, default=0)
    parser.add_argument("--outcome-samples", type=int, default=0)
    parser.add_argument("--eligible-outcomes", type=int, default=0)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--walk-forward", action="store_true")
    parser.add_argument("--regime-validation", action="store_true")
    parser.add_argument("--watchdog", action="store_true")
    parser.add_argument("--recovery", action="store_true")
    parser.add_argument("--execution-test", action="store_true")
    parser.add_argument("--critical-errors", type=int, default=0)
    args = parser.parse_args()
    report = RealReadinessGate().evaluate(
        mode=args.mode,
        preflight_ok=args.preflight,
        state_samples=args.state_samples,
        outcome_samples=args.outcome_samples,
        eligible_outcomes=args.eligible_outcomes,
        walk_forward_ok=args.walk_forward,
        regime_validation_ok=args.regime_validation,
        watchdog_ok=args.watchdog,
        recovery_ok=args.recovery,
        execution_test_ok=args.execution_test,
        critical_errors=args.critical_errors,
    )
    print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
