from PC_ENGINE.core.adaptive_job_gate import AdaptiveJobGate
from PC_ENGINE.core.adaptive_resource_manager import ResourcePolicy

def make_policy(backtests=1, simulations=1):
    return ResourcePolicy("BALANCED", 2, backtests, simulations, 1, 1024, False, ())

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

def test_compact_policy_defers_backtest_and_simulation():
    gate = AdaptiveJobGate(Manager(make_policy(0, 0)))
    with gate.slot("backtest") as backtest:
        assert not backtest
    with gate.slot("simulation") as simulation:
        assert not simulation

def test_probe_failure_fails_closed():
    with AdaptiveJobGate(Manager(error=True)).slot("backtest") as admitted:
        assert not admitted

def test_concurrency_limit_does_not_interrupt_active_job():
    gate = AdaptiveJobGate(Manager(make_policy(1, 1)))
    with gate.slot("backtest") as first:
        assert first
        with gate.slot("backtest") as second:
            assert not second
        assert gate.snapshot()["active"]["backtest"] == 1
    assert gate.snapshot()["active"]["backtest"] == 0

def test_invalid_job_kind_is_rejected():
    gate = AdaptiveJobGate(Manager())
    try:
        with gate.slot("training"):
            pass
    except ValueError as exc:
        assert "unsupported" in str(exc)
    else:
        raise AssertionError("invalid kind accepted")
