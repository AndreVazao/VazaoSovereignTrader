from __future__ import annotations

import json
import math
import statistics
import time
from pathlib import Path
from typing import Any

from PC_ENGINE.radar.hot_path_calibration import _moving_block_bootstrap_ci
from PC_ENGINE.radar.hot_path_walk_forward import _read_completed_paper, _valid_rows


def _ci_for_test(rows: list[dict[str, Any]], seed_key: str) -> dict[str, Any]:
    values = [float(row["realized_net_bps"]) for row in rows]
    if len(values) < 2:
        normal_lower = normal_upper = None
    else:
        mean = statistics.fmean(values)
        std = statistics.stdev(values)
        margin = 1.96 * std / math.sqrt(len(values))
        normal_lower, normal_upper = mean - margin, mean + margin

    bootstrap = _moving_block_bootstrap_ci(values, rows, seed_key=seed_key)
    if bootstrap["assessment"] == "AVAILABLE":
        return {
            "ci95_method": bootstrap["method"],
            "ci95_lower_bps": round(float(bootstrap["lower"]), 6),
            "ci95_upper_bps": round(float(bootstrap["upper"]), 6),
            "bootstrap_replicates": int(bootstrap["bootstrap_replicates"]),
            "bootstrap_block_length": int(bootstrap["block_length"]),
        }
    return {
        "ci95_method": "sample_normal",
        "ci95_lower_bps": round(normal_lower, 6) if normal_lower is not None else None,
        "ci95_upper_bps": round(normal_upper, 6) if normal_upper is not None else None,
        "bootstrap_replicates": 0,
        "bootstrap_block_length": None,
    }


def build_regime_walk_forward_report(
    outcomes_path: str | Path,
    *,
    train_size: int = 100,
    test_size: int = 25,
    step_size: int | None = None,
    min_test_samples: int = 10,
) -> dict[str, Any]:
    """Chronological PAPER-only OOS evidence, with observed-regime test breakdowns."""
    train_size = max(1, int(train_size))
    test_size = max(1, int(test_size))
    step_size = max(1, int(step_size or test_size))
    min_test_samples = max(1, int(min_test_samples))

    raw = _read_completed_paper(Path(outcomes_path))
    rows = _valid_rows(raw)
    folds: list[dict[str, Any]] = []

    start = train_size
    while start < len(rows):
        train = rows[max(0, start - train_size):start]
        test = rows[start:start + test_size]
        if len(test) < min_test_samples:
            break

        test_net = [float(row["realized_net_bps"]) for row in test]
        train_net = [float(row["realized_net_bps"]) for row in train]
        regime_groups: dict[str, list[dict[str, Any]]] = {}
        for row in test:
            regime_groups.setdefault(str(row["market_regime"]), []).append(row)

        regime_stats: list[dict[str, Any]] = []
        for regime, group in sorted(regime_groups.items()):
            values = [float(row["realized_net_bps"]) for row in group]
            mean = statistics.fmean(values)
            ci = _ci_for_test(group, f"{start}:{regime}")
            regime_stats.append({
                "market_regime": regime,
                "test_samples": len(group),
                "test_mean_realized_net_bps": round(mean, 6),
                "test_profitable_after_costs_rate": round(sum(v > 0 for v in values) / len(values), 6),
                **ci,
            })

        folds.append({
            "fold": len(folds) + 1,
            "train_samples": len(train),
            "test_samples": len(test),
            "train_start_ms": int(train[0]["outcome_local_ts_ms"]) if train else None,
            "train_end_ms": int(train[-1]["outcome_local_ts_ms"]) if train else None,
            "test_start_ms": int(test[0]["outcome_local_ts_ms"]),
            "test_end_ms": int(test[-1]["outcome_local_ts_ms"]),
            "train_mean_realized_net_bps": round(statistics.fmean(train_net), 6) if train_net else None,
            "test_mean_realized_net_bps": round(statistics.fmean(test_net), 6),
            "test_profitable_after_costs_rate": round(sum(v > 0 for v in test_net) / len(test_net), 6),
            "observed_market_regimes": sorted(regime_groups),
            "regime_test_stats": regime_stats,
        })
        start += step_size

    regime_coverage: dict[str, int] = {}
    for fold in folds:
        for regime in fold["observed_market_regimes"]:
            regime_coverage[regime] = regime_coverage.get(regime, 0) + 1

    return {
        "schema_version": 1,
        "generated_at_ms": time.time_ns() // 1_000_000,
        "source": Path(outcomes_path).name,
        "raw_completed_paper_records": len(raw),
        "timestamped_valid_records": len(rows),
        "train_size": train_size,
        "test_size": test_size,
        "step_size": step_size,
        "min_test_samples": min_test_samples,
        "folds": folds,
        "fold_count": len(folds),
        "regime_fold_coverage": regime_coverage,
        "paper_only": True,
        "orders_submitted": False,
        "execution_authorized": False,
        "note": "Evidence only. Test windows are strictly after training windows; observed market_regime metadata is reported as recorded and is not inferred from test outcomes or used to authorize execution. Confidence intervals are descriptive and not proof of future profitability.",
    }


def write_regime_walk_forward_report(
    outcomes_path: str | Path,
    report_path: str | Path,
    **kwargs: Any,
) -> dict[str, Any]:
    report = build_regime_walk_forward_report(outcomes_path, **kwargs)
    destination = Path(report_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2), encoding="utf-8")
    temporary.replace(destination)
    return report
