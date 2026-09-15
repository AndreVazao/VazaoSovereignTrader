from PC_ENGINE.core.real_readiness import RealReadinessGate

if __name__ == "__main__":
    report = RealReadinessGate().evaluate(mode="PAPER", preflight_ok=False, state_samples=0, outcome_samples=0, eligible_outcomes=0, walk_forward_ok=False, regime_validation_ok=False, watchdog_ok=False, recovery_ok=False, execution_test_ok=False)
    print(report.status)
    for blocker in report.blockers:
        print(f"BLOCKED: {blocker}")
