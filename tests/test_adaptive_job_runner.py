from PC_ENGINE.core.adaptive_job_runner import run_adaptive_simulation
from PC_ENGINE.core.adaptive_job_gate import AdaptiveJobDeferred
from PC_ENGINE.core.adaptive_resource_manager import ResourcePolicy


def _policy(simulations: int) -> ResourcePolicy:
    return ResourcePolicy("COMPACT" if simulations == 0 else "BALANCED", 1, 0, simulations, 1, 512, simulations == 0, ())


class _Manager:
    def __init__(self, policy=None, fail=False):
        self.policy = policy or _policy(1)
        self.fail = fail

    def refresh(self):
        if self.fail:
            raise OSError("resource probe unavailable")
        return self.policy


def test_simulation_gate_executes_job_when_budget_is_available(monkeypatch):
    from PC_ENGINE.core import adaptive_job_runner as runner
    monkeypatch.setattr(runner, "configured_adaptive_job_gate", lambda: __import__(
        "PC_ENGINE.core.adaptive_job_gate", fromlist=["AdaptiveJobGate"]
    ).AdaptiveJobGate(_Manager()))
    assert run_adaptive_simulation(lambda: "completed") == "completed"


def test_simulation_gate_does_not_start_job_when_budget_is_zero(monkeypatch):
    from PC_ENGINE.core import adaptive_job_runner as runner
    from PC_ENGINE.core.adaptive_job_gate import AdaptiveJobGate
    monkeypatch.setattr(runner, "configured_adaptive_job_gate", lambda: AdaptiveJobGate(_Manager(_policy(0))))
    called = []
    try:
        run_adaptive_simulation(lambda: called.append(True))
    except AdaptiveJobDeferred:
        pass
    else:
        raise AssertionError("zero budget must defer")
    assert called == []


def test_simulation_gate_fails_closed_when_probe_fails(monkeypatch):
    from PC_ENGINE.core import adaptive_job_runner as runner
    from PC_ENGINE.core.adaptive_job_gate import AdaptiveJobGate
    monkeypatch.setattr(runner, "configured_adaptive_job_gate", lambda: AdaptiveJobGate(_Manager(fail=True)))
    try:
        run_adaptive_simulation(lambda: "must not run")
    except AdaptiveJobDeferred:
        pass
    else:
        raise AssertionError("failed probe must defer")
