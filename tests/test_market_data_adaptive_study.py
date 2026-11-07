from PC_ENGINE.tools import run_market_data_collector as collector
from PC_ENGINE.core import adaptive_job_runner
from PC_ENGINE.core.adaptive_job_gate import AdaptiveJobDeferred


def test_optional_study_runs_when_adaptive_budget_admits(monkeypatch):
    monkeypatch.setattr(adaptive_job_runner, "run_adaptive_simulation", lambda job: job())
    called = []
    result = collector._run_study_with_resource_budget(lambda: called.append("ran") or {"samples": 12})
    assert result == {"samples": 12}
    assert called == ["ran"]


def test_optional_study_is_deferred_without_loading_or_computing(monkeypatch):
    def defer(_job):
        raise AdaptiveJobDeferred("COMPACT profile has no simulation budget")

    monkeypatch.setattr(adaptive_job_runner, "run_adaptive_simulation", defer)
    called = []
    result = collector._run_study_with_resource_budget(lambda: called.append("must-not-run"))
    assert result["deferred"] is True
    assert "COMPACT" in result["reason"]
    assert called == []
