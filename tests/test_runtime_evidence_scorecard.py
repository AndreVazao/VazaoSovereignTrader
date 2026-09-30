from __future__ import annotations

import json

from PC_ENGINE.diagnostics.evidence_scorecard import build_runtime_evidence_scorecard


def test_runtime_evidence_scorecard_fails_closed_when_reports_are_missing(tmp_path):
    report = build_runtime_evidence_scorecard({"radar": {"data_dir": str(tmp_path)}})

    assert report["requirements_met"] == 0
    assert report["requirements_total"] > 0
    assert report["execution_authorized"] is False
    assert report["paper_only"] is True
    assert report["orders_submitted"] is False
    assert all(item["status"] == "MISSING" for item in report["checks"])
    assert report["report_paths"]["calibration"].endswith("hot_path_calibration.json")


def test_runtime_evidence_scorecard_uses_configured_report_paths(tmp_path):
    reports = tmp_path / "reports"
    reports.mkdir()
    paths = {
        "calibration": reports / "cal.json",
        "walk_forward": reports / "wf.json",
        "regime_walk_forward": reports / "regime.json",
        "oos_robustness": reports / "oos.json",
    }
    for path in paths.values():
        path.write_text(json.dumps({}), encoding="utf-8")

    report = build_runtime_evidence_scorecard({
        "radar": {
            "data_dir": str(tmp_path / "default"),
            "evidence_reports": {key: str(path) for key, path in paths.items()},
        }
    })

    assert report["requirements_met"] == 0
    assert report["execution_authorized"] is False
    assert report["report_paths"]["calibration"] == str(paths["calibration"])
