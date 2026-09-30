from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any


def _load_json(path: str | Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    source = Path(path)
    if not source.exists():
        return None
    try:
        value = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _status(requirement: str, observed: Any, passed: bool, detail: str) -> dict[str, Any]:
    return {
        "requirement": requirement,
        "status": "MET" if passed else "MISSING",
        "observed": observed,
        "detail": detail,
    }


def build_evidence_scorecard(
    *,
    calibration_report_path: str | Path | None = None,
    walk_forward_report_path: str | Path | None = None,
    regime_walk_forward_report_path: str | Path | None = None,
    oos_robustness_report_path: str | Path | None = None,
    min_calibration_samples: int = 100,
    min_walk_forward_folds: int = 4,
    min_regime_folds: int = 4,
    require_cost_scenario_bps: float = 2.0,
) -> dict[str, Any]:
    """Assemble an auditable evidence checklist; it never authorizes execution."""
    min_calibration_samples = max(1, int(min_calibration_samples))
    min_walk_forward_folds = max(1, int(min_walk_forward_folds))
    min_regime_folds = max(1, int(min_regime_folds))
    require_cost_scenario_bps = max(0.0, float(require_cost_scenario_bps))

    calibration = _load_json(calibration_report_path)
    walk_forward = _load_json(walk_forward_report_path)
    regime = _load_json(regime_walk_forward_report_path)
    robustness = _load_json(oos_robustness_report_path)

    checks: list[dict[str, Any]] = []

    calibration_samples = int(calibration.get("outcome_samples", 0)) if calibration else 0
    checks.append(_status(
        "calibration_samples",
        calibration_samples,
        calibration is not None and calibration_samples >= min_calibration_samples,
        f"requires >= {min_calibration_samples} valid unique PAPER outcome samples",
    ))

    duplicate_count = int(calibration.get("duplicate_outcomes_ignored", 0)) if calibration else 0
    invalid_count = int(calibration.get("invalid_outcomes_ignored", 0)) if calibration else 0
    checks.append(_status(
        "data_integrity_accounting",
        {"duplicates_ignored": duplicate_count, "invalid_ignored": invalid_count},
        calibration is not None and "duplicate_outcomes_ignored" in calibration and "invalid_outcomes_ignored" in calibration,
        "duplicate and invalid PAPER outcomes are explicitly accounted for",
    ))

    wf_folds = int(walk_forward.get("fold_count", 0)) if walk_forward else 0
    checks.append(_status(
        "chronological_walk_forward",
        wf_folds,
        walk_forward is not None and wf_folds >= min_walk_forward_folds,
        f"requires >= {min_walk_forward_folds} chronological OOS folds",
    ))

    regime_folds = int(regime.get("fold_count", 0)) if regime else 0
    regime_coverage = regime.get("regime_fold_coverage", {}) if regime else {}
    checks.append(_status(
        "regime_stratification",
        {"folds": regime_folds, "regimes": sorted(regime_coverage) if isinstance(regime_coverage, dict) else []},
        regime is not None and regime_folds >= min_regime_folds and isinstance(regime_coverage, dict) and bool(regime_coverage),
        f"requires >= {min_regime_folds} regime-aware OOS folds and observed regime coverage",
    ))

    temporal_available = False
    if calibration:
        temporal_available = any(
            isinstance(row, dict) and row.get("temporal_dependence_assessment") == "AVAILABLE"
            for row in calibration.get("stats", [])
        )
    checks.append(_status(
        "temporal_dependence_evidence",
        temporal_available,
        calibration is not None and temporal_available,
        "at least one calibration group has timestamped temporal-dependence evidence",
    ))

    bootstrap_available = False
    if calibration:
        bootstrap_available = any(
            isinstance(row, dict) and row.get("ci95_method") == "moving_block_bootstrap"
            for row in calibration.get("stats", [])
        )
    checks.append(_status(
        "bootstrap_confidence_intervals",
        bootstrap_available,
        calibration is not None and bootstrap_available,
        "at least one calibration group has a moving-block bootstrap CI",
    ))

    cost_scenarios = robustness.get("scenarios", []) if robustness else []
    matching_cost = next(
        (
            row for row in cost_scenarios
            if isinstance(row, dict)
            and math.isclose(float(row.get("extra_cost_bps", -1.0)), require_cost_scenario_bps, abs_tol=1e-9)
        ),
        None,
    )
    checks.append(_status(
        "cost_stress",
        {
            "required_extra_cost_bps": require_cost_scenario_bps,
            "scenario_present": matching_cost is not None,
            "scenario_samples": int(matching_cost.get("samples", 0)) if matching_cost else 0,
        },
        robustness is not None and matching_cost is not None and int(matching_cost.get("samples", 0)) > 0,
        f"requires an OOS extra-cost scenario at {require_cost_scenario_bps:g} bps with observations",
    ))

    monte_carlo_available = bool(
        matching_cost
        and matching_cost.get("monte_carlo_method") == "moving_block_bootstrap"
        and int(matching_cost.get("monte_carlo_replicates", 0)) >= 500
    )
    checks.append(_status(
        "bootstrap_monte_carlo",
        {
            "method": matching_cost.get("monte_carlo_method") if matching_cost else None,
            "replicates": int(matching_cost.get("monte_carlo_replicates", 0)) if matching_cost else 0,
        },
        robustness is not None and monte_carlo_available,
        "requires deterministic moving-block bootstrap resampling with >= 500 replicates",
    ))

    oos_only = bool(
        robustness
        and robustness.get("paper_only") is True
        and robustness.get("orders_submitted") is False
    )
    checks.append(_status(
        "paper_only_oos",
        {
            "paper_only": robustness.get("paper_only") if robustness else None,
            "orders_submitted": robustness.get("orders_submitted") if robustness else None,
        },
        oos_only,
        "OOS robustness evidence must be explicitly PAPER-only with no submitted orders",
    ))

    checks.append(_status(
        "execution_authorization",
        False,
        False,
        "always remains separate: this scorecard cannot authorize REAL execution",
    ))

    missing = [item["requirement"] for item in checks if item["status"] != "MET"]
    return {
        "schema_version": 1,
        "generated_at_ms": time.time_ns() // 1_000_000,
        "requirements_met": len(checks) - len(missing),
        "requirements_total": len(checks),
        "requirements_missing": missing,
        "checks": checks,
        "paper_only": True,
        "orders_submitted": False,
        "execution_authorized": False,
        "note": "Auditable evidence checklist only. MET means the configured evidence requirement is present; it does not mean profitability is established, guarantee future returns, or authorize REAL execution.",
    }


def write_evidence_scorecard(
    report_path: str | Path,
    **kwargs: Any,
) -> dict[str, Any]:
    report = build_evidence_scorecard(**kwargs)
    destination = Path(report_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2), encoding="utf-8")
    temporary.replace(destination)
    return report
