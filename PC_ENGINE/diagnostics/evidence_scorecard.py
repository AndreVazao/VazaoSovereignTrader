from __future__ import annotations

from pathlib import Path
from typing import Any

from PC_ENGINE.radar.hot_path_evidence_scorecard import build_evidence_scorecard


def build_runtime_evidence_scorecard(config: dict[str, Any]) -> dict[str, Any]:
    """Build a read-only runtime view of evidence reports; never authorizes execution."""
    radar = config.get("radar", {})
    data_dir = Path(radar.get("data_dir", "PC_ENGINE/data/radar"))
    report_cfg = radar.get("evidence_reports", {})

    def report_path(key: str, default_name: str) -> Path:
        configured = report_cfg.get(key)
        return Path(configured) if configured else data_dir / default_name

    report = build_evidence_scorecard(
        calibration_report_path=report_path("calibration", "hot_path_calibration.json"),
        walk_forward_report_path=report_path("walk_forward", "hot_path_walk_forward.json"),
        regime_walk_forward_report_path=report_path("regime_walk_forward", "hot_path_regime_walk_forward.json"),
        oos_robustness_report_path=report_path("oos_robustness", "hot_path_oos_robustness.json"),
        min_calibration_samples=int(radar.get("evidence_min_calibration_samples", 100)),
        min_walk_forward_folds=int(radar.get("evidence_min_walk_forward_folds", 4)),
        min_regime_folds=int(radar.get("evidence_min_regime_folds", 4)),
        require_cost_scenario_bps=float(radar.get("evidence_required_extra_cost_bps", 2.0)),
    )
    report["report_paths"] = {
        "calibration": str(report_path("calibration", "hot_path_calibration.json")),
        "walk_forward": str(report_path("walk_forward", "hot_path_walk_forward.json")),
        "regime_walk_forward": str(report_path("regime_walk_forward", "hot_path_regime_walk_forward.json")),
        "oos_robustness": str(report_path("oos_robustness", "hot_path_oos_robustness.json")),
    }
    return report
