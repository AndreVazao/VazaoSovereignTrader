from __future__ import annotations

import json

from PC_ENGINE.diagnostics.evidence_scorecard import refresh_runtime_evidence_reports


def test_refresh_generates_paper_reports_without_authorizing_execution(tmp_path):
    report = refresh_runtime_evidence_reports({
        "radar": {
            "data_dir": str(tmp_path),
            "hot_path_outcomes_path": str(tmp_path / "missing_outcomes.jsonl"),
            "evidence_train_size": 4,
            "evidence_test_size": 2,
            "evidence_min_test_samples": 2,
        }
    })

    assert report["outcomes_file_exists"] is False
    assert report["paper_only"] is True
    assert report["orders_submitted"] is False
    assert report["execution_authorized"] is False
    assert report["scorecard"]["execution_authorized"] is False
    for name, filename in (
        ("calibration", "hot_path_calibration.json"),
        ("walk_forward", "hot_path_walk_forward.json"),
        ("regime_walk_forward", "hot_path_regime_walk_forward.json"),
        ("oos_robustness", "hot_path_oos_robustness.json"),
    ):
        path = tmp_path / filename
        assert path.exists(), name
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["paper_only"] is True
        assert payload["orders_submitted"] is False
        assert payload["execution_authorized"] is False



def test_relative_configured_paths_resolve_from_repository_root(tmp_path, monkeypatch):
    from PC_ENGINE.diagnostics import path_utils

    monkeypatch.setattr(path_utils, "REPO_ROOT", tmp_path)
    report = refresh_runtime_evidence_reports({
        "radar": {
            "data_dir": "runtime/radar",
            "hot_path_outcomes_path": "runtime/custom-outcomes.jsonl",
            "evidence_reports": {"calibration": "reports/custom-calibration.json"},
            "evidence_train_size": 4,
            "evidence_test_size": 2,
            "evidence_min_test_samples": 2,
        }
    })

    assert report["outcomes_path"] == str(tmp_path / "runtime/custom-outcomes.jsonl")
    assert report["outcomes_file_exists"] is False
    assert (tmp_path / "reports/custom-calibration.json").is_file()
    assert (tmp_path / "runtime/radar/hot_path_walk_forward.json").is_file()
    assert report["scorecard"]["report_paths"]["calibration"] == str(tmp_path / "reports/custom-calibration.json")


def test_collector_honours_configured_outcomes_path(tmp_path, monkeypatch):
    from PC_ENGINE.tools import run_market_data_collector as collector

    monkeypatch.setattr(collector, "REPO_ROOT", tmp_path)
    radar_cfg = {"hot_path_outcomes_path": "runtime/custom-outcomes.jsonl"}
    data_dir = tmp_path / "runtime" / "radar"

    assert collector._outcomes_path(radar_cfg, data_dir) == tmp_path / "runtime/custom-outcomes.jsonl"
    assert collector._outcomes_path({}, data_dir) == data_dir / "hot_path_outcomes.jsonl"


def test_refresh_survives_corrupt_utf8_and_json_lines_in_outcomes(tmp_path):
    outcomes = tmp_path / "corrupt-outcomes.jsonl"
    outcomes.write_bytes(b"\xff\xfe\n{bad json\n")
    result = refresh_runtime_evidence_reports({
        "radar": {
            "data_dir": str(tmp_path),
            "hot_path_outcomes_path": str(outcomes),
            "evidence_train_size": 2,
            "evidence_test_size": 2,
            "evidence_min_test_samples": 2,
        }
    })
    assert result["outcomes_file_exists"] is True
    assert result["paper_only"] is True
    assert result["execution_authorized"] is False
    assert result["reports"]["calibration"]["outcome_samples"] == 0
    assert result["reports"]["walk_forward"]["timestamped_valid_records"] == 0
