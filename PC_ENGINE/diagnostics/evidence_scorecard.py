from __future__ import annotations

from pathlib import Path
from typing import Any

from PC_ENGINE.radar.hot_path_evidence_scorecard import build_evidence_scorecard
from PC_ENGINE.radar.hot_path_calibration import write_hot_path_calibration
from PC_ENGINE.radar.hot_path_walk_forward import write_walk_forward_report
from PC_ENGINE.radar.hot_path_regime_walk_forward import write_regime_walk_forward_report
from PC_ENGINE.radar.hot_path_oos_robustness import write_oos_robustness_report
from PC_ENGINE.diagnostics.path_utils import resolve_config_path


def build_runtime_evidence_scorecard(config: dict[str, Any]) -> dict[str, Any]:
    """Build a read-only runtime view of evidence reports; never authorizes execution."""
    radar = config.get("radar", {})
    data_dir = resolve_config_path(radar.get("data_dir", "PC_ENGINE/data/radar"))
    report_cfg = radar.get("evidence_reports", {})

    def report_path(key: str, default_name: str) -> Path:
        configured = report_cfg.get(key)
        return resolve_config_path(configured) if configured else data_dir / default_name

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


def refresh_runtime_evidence_reports(config: dict[str, Any]) -> dict[str, Any]:
    """Refresh local evidence artifacts from completed PAPER outcomes only."""
    radar = config.get("radar", {})
    data_dir = resolve_config_path(radar.get("data_dir", "PC_ENGINE/data/radar"))
    report_cfg = radar.get("evidence_reports", {})
    outcomes_path = resolve_config_path(radar.get("hot_path_outcomes_path", data_dir / "hot_path_outcomes.jsonl"))

    def report_path(key: str, default_name: str) -> Path:
        configured = report_cfg.get(key)
        return resolve_config_path(configured) if configured else data_dir / default_name

    train_size = max(1, int(radar.get("evidence_train_size", 100)))
    test_size = max(1, int(radar.get("evidence_test_size", 25)))
    step_size = max(1, int(radar.get("evidence_step_size", test_size)))
    min_test_samples = max(1, int(radar.get("evidence_min_test_samples", 10)))

    generated: dict[str, Any] = {
        "outcomes_path": str(outcomes_path),
        "outcomes_file_exists": outcomes_path.exists(),
        "reports": {},
    }
    generated["reports"]["calibration"] = write_hot_path_calibration(
        outcomes_path,
        report_path("calibration", "hot_path_calibration.json"),
        min_samples=int(radar.get("evidence_min_calibration_samples", 100)),
    )
    generated["reports"]["walk_forward"] = write_walk_forward_report(
        outcomes_path,
        report_path("walk_forward", "hot_path_walk_forward.json"),
        train_size=train_size,
        test_size=test_size,
        step_size=step_size,
        min_test_samples=min_test_samples,
    )
    generated["reports"]["regime_walk_forward"] = write_regime_walk_forward_report(
        outcomes_path,
        report_path("regime_walk_forward", "hot_path_regime_walk_forward.json"),
        train_size=train_size,
        test_size=test_size,
        step_size=step_size,
        min_test_samples=min_test_samples,
    )
    generated["reports"]["oos_robustness"] = write_oos_robustness_report(
        outcomes_path,
        report_path("oos_robustness", "hot_path_oos_robustness.json"),
        train_size=train_size,
        test_size=test_size,
        step_size=step_size,
        min_test_samples=min_test_samples,
    )
    generated["scorecard"] = build_runtime_evidence_scorecard(config)
    generated["paper_only"] = True
    generated["orders_submitted"] = False
    generated["execution_authorized"] = False
    return generated
