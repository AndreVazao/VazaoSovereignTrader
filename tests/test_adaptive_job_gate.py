from PC_ENGINE.core.adaptive_job_gate import AdaptiveJobGate
from PC_ENGINE.core.adaptive_resource_manager import ResourcePolicy


def make_policy(backtests=1, simulations=1, analysis=1):
    return ResourcePolicy("BALANCED", 2, backtests, simulations, analysis, 1024, False, ())


class Manager:
    def __init__(self, policy=None, error=False):
        self.policy = policy or make_policy()
        self.error = error

    def refresh(self):
        if self.error:
            raise OSError("probe failed")
        return self.policy


def test_backtest_slot_is_granted_and_released():
    gate = AdaptiveJobGate(Manager())
    with gate.slot("backtest") as admitted:
        assert admitted
        assert gate.snapshot()["active"]["backtest"] == 1
    assert gate.snapshot()["active"]["backtest"] == 0


def test_analysis_slot_is_granted_and_released():
    gate = AdaptiveJobGate(Manager())
    with gate.slot("analysis") as admitted:
        assert admitted
        assert gate.snapshot()["active"]["analysis"] == 1
    assert gate.snapshot()["active"]["analysis"] == 0


def test_compact_policy_defers_backtest_simulation_and_analysis():
    gate = AdaptiveJobGate(Manager(make_policy(0, 0, 0)))
    for kind in ("backtest", "simulation", "analysis"):
        with gate.slot(kind) as admitted:
            assert not admitted


def test_probe_failure_fails_closed():
    with AdaptiveJobGate(Manager(error=True)).slot("backtest") as admitted:
        assert not admitted


def test_concurrency_limit_does_not_interrupt_active_job():
    gate = AdaptiveJobGate(Manager(make_policy(1, 1, 1)))
    with gate.slot("backtest") as first:
        assert first
        with gate.slot("backtest") as second:
            assert not second
        assert gate.snapshot()["active"]["backtest"] == 1
    assert gate.snapshot()["active"]["backtest"] == 0


def test_invalid_job_kind_is_rejected():
    try:
        with AdaptiveJobGate(Manager()).slot("training"):
            pass
    except ValueError as exc:
        assert "unsupported" in str(exc)
    else:
        raise AssertionError("invalid kind accepted")
