from __future__ import annotations

import sys

import pytest

from PC_ENGINE.core.adaptive_job_gate import AdaptiveJobDeferred
from PC_ENGINE.tools import run_lead_lag_validation, run_readiness_pipeline, run_regime_validation


def _defer(job):
    raise AdaptiveJobDeferred("analysis budget unavailable")


def test_regime_validation_defers_before_evaluation(monkeypatch):
    constructed = []
    evaluated = []

    class Validator:
        def __init__(self, **kwargs):
            constructed.append(True)

        def evaluate(self):
            evaluated.append(True)
            return {}

    monkeypatch.setattr(run_regime_validation, "RegimeAwareValidator", Validator)
    monkeypatch.setattr(run_regime_validation, "run_adaptive_analysis", _defer)
    monkeypatch.setattr(sys, "argv", ["run_regime_validation.py"])

    with pytest.raises(SystemExit, match="deferred safely"):
        run_regime_validation.main()

    assert constructed == []
    assert evaluated == []


def test_lead_lag_validation_defers_before_evaluation(monkeypatch):
    constructed = []
    evaluated = []

    class Validator:
        def __init__(self, *args, **kwargs):
            constructed.append(True)

        def validate(self, horizon_ms):
            evaluated.append(horizon_ms)
            return []

    monkeypatch.setattr(run_lead_lag_validation, "LeadLagValidationEngine", Validator)
    monkeypatch.setattr(run_lead_lag_validation, "run_adaptive_analysis", _defer)
    monkeypatch.setattr(sys, "argv", ["run_lead_lag_validation.py"])

    with pytest.raises(SystemExit, match="deferred safely"):
        run_lead_lag_validation.main()

    assert constructed == []
    assert evaluated == []


def test_readiness_pipeline_does_not_read_or_overwrite_artifacts_when_deferred(tmp_path, monkeypatch):
    validation_dir = tmp_path / "validation"
    validation_dir.mkdir()
    state_artifact = tmp_path / "state_outcomes.jsonl"
    walk_artifact = validation_dir / "walk_forward.json"
    regime_artifact = validation_dir / "regime_validation.json"
    state_artifact.write_text("preserve-state\\n", encoding="utf-8")
    walk_artifact.write_text("preserve-walk\\n", encoding="utf-8")
    regime_artifact.write_text("preserve-regime\\n", encoding="utf-8")

    read_attempts = []

    def unexpected_read(path):
        read_attempts.append(path)
        raise AssertionError("market state history must not be loaded before budget admission")

    monkeypatch.setattr(run_readiness_pipeline, "_read_jsonl", unexpected_read)
    monkeypatch.setattr(run_readiness_pipeline, "run_adaptive_analysis", _defer)

    with pytest.raises(AdaptiveJobDeferred):
        run_readiness_pipeline.run(data_dir=tmp_path)

    assert read_attempts == []
    assert state_artifact.read_text(encoding="utf-8") == "preserve-state\\n"
    assert walk_artifact.read_text(encoding="utf-8") == "preserve-walk\\n"
    assert regime_artifact.read_text(encoding="utf-8") == "preserve-regime\\n"
