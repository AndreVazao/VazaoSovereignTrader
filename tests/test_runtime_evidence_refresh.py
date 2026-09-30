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
