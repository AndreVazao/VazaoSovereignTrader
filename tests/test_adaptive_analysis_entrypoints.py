from __future__ import annotations

import sys

import pytest

from PC_ENGINE.core.adaptive_job_gate import AdaptiveJobDeferred
from PC_ENGINE.tools import run_lead_lag_validation, run_readiness_pipeline, run_regime_validation


def _defer(job):
    raise AdaptiveJobDeferred("analysis budget unavailable")


def test_regime_validation_defers_before_evaluation(monkeypatch):
    evaluated = []

    class Validator:
        def __init__(self, **kwargs):
            pass

        def evaluate(self):
            evaluated.append(True)
            return {}

    monkeypatch.setattr(run_regime_validation, "RegimeAwareValidator", Validator)
    monkeypatch.setattr(run_regime_validation, "run_adaptive_analysis", _defer)
    monkeypatch.setattr(sys, "argv", ["run_regime_validation.py"])

    with pytest.raises(SystemExit, match="deferred safely"):
        run_regime_validation.main()

    assert evaluated == []


def test_lead_lag_validation_defers_before_evaluation(monkeypatch):
    evaluated = []

    class Validator:
        def __init__(self, *args, **kwargs):
            pass

        def validate(self, horizon_ms):
            evaluated.append(horizon_ms)
            return []

    monkeypatch.setattr(run_lead_lag_validation, "LeadLagValidationEngine", Validator)
    monkeypatch.setattr(run_lead_lag_validation, "run_adaptive_analysis", _defer)
    monkeypatch.setattr(sys, "argv", ["run_lead_lag_validation.py"])

    with pytest.raises(SystemExit, match="deferred safely"):
        run_lead_lag_validation.main()

    assert evaluated == []


def test_readiness_pipeline_does_not_write_partial_artifacts_when_deferred(tmp_path, monkeypatch):
    monkeypatch.setattr(run_readiness_pipeline, "run_adaptive_analysis", _defer)

    with pytest.raises(AdaptiveJobDeferred):
        run_readiness_pipeline.run(data_dir=tmp_path)

    assert not (tmp_path / "state_outcomes.jsonl").exists()
    assert not (tmp_path / "validation" / "walk_forward.json").exists()
    assert not (tmp_path / "validation" / "regime_validation.json").exists()
