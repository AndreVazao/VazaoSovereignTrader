from PC_ENGINE.core.adaptive_job_runner import run_adaptive_analysis, run_adaptive_simulation
from PC_ENGINE.core.adaptive_job_gate import AdaptiveJobDeferred
from PC_ENGINE.core.adaptive_resource_manager import ResourcePolicy


def _policy(simulations: int, analysis: int = 1) -> ResourcePolicy:
    compact = simulations == 0 and analysis == 0
    return ResourcePolicy(
        "COMPACT" if compact else "BALANCED",
        1,
        0,
        simulations,
        analysis,
        512,
        compact,
        (),
    )


class _Manager:
    def __init__(self, policy=None, fail=False):
        self.policy = policy or _policy(1)
        self.fail = fail

    def refresh(self):
        if self.fail:
            raise OSError("resource probe unavailable")
        return self.policy


def _install_gate(monkeypatch, manager):
    from PC_ENGINE.core import adaptive_job_runner as runner
    from PC_ENGINE.core.adaptive_job_gate import AdaptiveJobGate

    monkeypatch.setattr(
        runner,
        "configured_adaptive_job_gate",
        lambda: AdaptiveJobGate(manager),
    )


def test_simulation_gate_executes_job_when_budget_is_available(monkeypatch):
    _install_gate(monkeypatch, _Manager())
    assert run_adaptive_simulation(lambda: "completed") == "completed"


def test_simulation_gate_does_not_start_job_when_budget_is_zero(monkeypatch):
    _install_gate(monkeypatch, _Manager(_policy(0)))
    called = []
    try:
        run_adaptive_simulation(lambda: called.append(True))
    except AdaptiveJobDeferred:
        pass
    else:
        raise AssertionError("zero budget must defer")
    assert called == []


def test_simulation_gate_fails_closed_when_probe_fails(monkeypatch):
    _install_gate(monkeypatch, _Manager(fail=True))
    try:
        run_adaptive_simulation(lambda: "must not run")
    except AdaptiveJobDeferred:
        pass
    else:
        raise AssertionError("failed probe must defer")


def test_analysis_gate_executes_job_when_budget_is_available(monkeypatch):
    _install_gate(monkeypatch, _Manager(_policy(1, analysis=1)))
    assert run_adaptive_analysis(lambda: "analyzed") == "analyzed"


def test_analysis_gate_does_not_start_job_when_budget_is_zero(monkeypatch):
    _install_gate(monkeypatch, _Manager(_policy(1, analysis=0)))
    called = []
    try:
        run_adaptive_analysis(lambda: called.append(True))
    except AdaptiveJobDeferred:
        pass
    else:
        raise AssertionError("zero analysis budget must defer")
    assert called == []


def test_analysis_gate_fails_closed_when_probe_fails(monkeypatch):
    _install_gate(monkeypatch, _Manager(fail=True))
    try:
        run_adaptive_analysis(lambda: "must not run")
    except AdaptiveJobDeferred:
        pass
    else:
        raise AssertionError("failed probe must defer")
