from __future__ import annotations

import json

from PC_ENGINE.radar.hot_path_evidence_scorecard import build_evidence_scorecard


def _write(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")


def test_scorecard_requires_all_evidence_layers(tmp_path):
    calibration = tmp_path / "calibration.json"
    walk = tmp_path / "walk.json"
    regime = tmp_path / "regime.json"
    robustness = tmp_path / "robustness.json"

    _write(calibration, {
        "outcome_samples": 120,
        "duplicate_outcomes_ignored": 2,
        "invalid_outcomes_ignored": 1,
        "stats": [{
            "temporal_dependence_assessment": "AVAILABLE",
            "ci95_method": "moving_block_bootstrap",
        }],
    })
    _write(walk, {"fold_count": 5})
    _write(regime, {"fold_count": 5, "regime_fold_coverage": {"TRENDING": 3, "RANGING": 2}})
    _write(robustness, {
        "paper_only": True,
        "orders_submitted": False,
        "scenarios": [{
            "extra_cost_bps": 2.0,
            "samples": 100,
            "monte_carlo_method": "moving_block_bootstrap",
            "monte_carlo_replicates": 2000,
        }],
    })

    report = build_evidence_scorecard(
        calibration_report_path=calibration,
        walk_forward_report_path=walk,
        regime_walk_forward_report_path=regime,
        oos_robustness_report_path=robustness,
    )

    assert report["requirements_missing"] == ["execution_authorization"]
    assert report["execution_authorized"] is False
    assert report["paper_only"] is True


def test_scorecard_does_not_treat_missing_reports_as_ready(tmp_path):
    report = build_evidence_scorecard(
        calibration_report_path=tmp_path / "missing-calibration.json",
        walk_forward_report_path=tmp_path / "missing-walk.json",
        regime_walk_forward_report_path=tmp_path / "missing-regime.json",
        oos_robustness_report_path=tmp_path / "missing-robustness.json",
    )

    assert report["requirements_met"] == 0
    assert "calibration_samples" in report["requirements_missing"]
    assert "cost_stress" in report["requirements_missing"]
    assert report["execution_authorized"] is False


def test_scorecard_fails_closed_on_invalid_utf8_and_malformed_numeric_fields(tmp_path):
    bad_utf8 = tmp_path / "bad-utf8.json"
    bad_utf8.write_bytes(b'{"outcome_samples":100}\xff')
    calibration = tmp_path / "calibration.json"
    walk = tmp_path / "walk.json"
    regime = tmp_path / "regime.json"
    robustness = tmp_path / "robustness.json"
    calibration.write_text(json.dumps({
        "outcome_samples": "not-a-number",
        "duplicate_outcomes_ignored": None,
        "invalid_outcomes_ignored": [],
        "stats": {"unexpected": "shape"},
    }), encoding="utf-8")
    walk.write_text(json.dumps({"fold_count": "NaN"}), encoding="utf-8")
    regime.write_text(json.dumps({"fold_count": [], "regime_fold_coverage": []}), encoding="utf-8")
    robustness.write_text(json.dumps({
        "paper_only": True,
        "orders_submitted": False,
        "scenarios": [
            {"extra_cost_bps": "not-a-number", "samples": "NaN", "monte_carlo_replicates": []}
        ],
    }), encoding="utf-8")
    missing = build_evidence_scorecard(calibration_report_path=bad_utf8)
    report = build_evidence_scorecard(
        calibration_report_path=calibration,
        walk_forward_report_path=walk,
        regime_walk_forward_report_path=regime,
        oos_robustness_report_path=robustness,
    )
    assert missing["requirements_met"] == 0
    assert report["execution_authorized"] is False
    assert "calibration_samples" in report["requirements_missing"]
    assert "chronological_walk_forward" in report["requirements_missing"]
    assert "cost_stress" in report["requirements_missing"]
    assert "data_integrity_accounting" in report["requirements_missing"]
