from __future__ import annotations

import hashlib
import math
import random
import statistics
import time
from pathlib import Path
from typing import Any

from PC_ENGINE.radar.hot_path_walk_forward import _read_completed_paper, _valid_rows
from PC_ENGINE.radar.report_io import atomic_write_json


def _block_bootstrap_means(
    values: list[float], *, seed_key: str, replicates: int = 2000
) -> list[float]:
    ordered = list(values)
    n = len(ordered)
    if n < 4:
        return []
    block_length = max(2, min(n // 2, int(round(math.sqrt(n)))))
    starts = list(range(n - block_length + 1))
    seed = int.from_bytes(hashlib.sha256(seed_key.encode("utf-8")).digest()[:8], "big")
    rng = random.Random(seed)
    output: list[float] = []
    for _ in range(max(500, int(replicates))):
        sample: list[float] = []
        while len(sample) < n:
            start = rng.choice(starts)
            sample.extend(ordered[start:start + block_length])
        output.append(statistics.fmean(sample[:n]))
    return output


def _percentile(sorted_values: list[float], probability: float) -> float:
    if not sorted_values:
        raise ValueError("empty sample")
    index = probability * (len(sorted_values) - 1)
    low = math.floor(index)
    high = math.ceil(index)
    if low == high:
        return sorted_values[low]
    weight = index - low
    return sorted_values[low] * (1.0 - weight) + sorted_values[high] * weight


def build_oos_robustness_report(
    outcomes_path: str | Path,
    *,
    train_size: int = 100,
    test_size: int = 25,
    step_size: int | None = None,
    min_test_samples: int = 10,
    extra_cost_scenarios_bps: tuple[float, ...] = (0.0, 0.5, 1.0, 2.0, 3.0),
    monte_carlo_replicates: int = 2000,
) -> dict[str, Any]:
    """Stress chronological PAPER OOS outcomes against extra costs and block-bootstrap uncertainty."""
    train_size = max(1, int(train_size))
    test_size = max(1, int(test_size))
    step_size = max(1, int(step_size or test_size))
    min_test_samples = max(1, int(min_test_samples))
    scenarios = tuple(sorted({max(0.0, float(value)) for value in extra_cost_scenarios_bps}))

    raw = _read_completed_paper(Path(outcomes_path))
    rows = _valid_rows(raw)
    folds: list[list[dict[str, Any]]] = []
    start = train_size
    while start < len(rows):
        train = rows[max(0, start - train_size):start]
        test = rows[start:start + test_size]
        if len(test) < min_test_samples:
            break
        if train:
            folds.append(test)
        start += step_size

    scenario_reports: list[dict[str, Any]] = []
    for extra_cost in scenarios:
        adjusted: list[float] = []
        fold_means: list[float] = []
        profitable_count = 0
        total_count = 0
        for fold_index, fold in enumerate(folds, start=1):
            values = [
                float(row["realized_net_bps"]) - extra_cost
                for row in fold
            ]
            adjusted.extend(values)
            fold_means.append(statistics.fmean(values))
            profitable_count += sum(value > 0.0 for value in values)
            total_count += len(values)

        simulation = _block_bootstrap_means(
            adjusted,
            seed_key=f"oos-robustness:{Path(outcomes_path).name}:{extra_cost:.6f}",
            replicates=monte_carlo_replicates,
        )
        simulation.sort()
        mean_net = statistics.fmean(adjusted) if adjusted else None
        scenario_reports.append({
            "extra_cost_bps": round(extra_cost, 6),
            "samples": len(adjusted),
            "folds": len(folds),
            "mean_adjusted_realized_net_bps": round(mean_net, 6) if mean_net is not None else None,
            "profitable_after_scenario_cost_rate": round(profitable_count / total_count, 6) if total_count else None,
            "positive_fold_rate": round(
                sum(value > 0.0 for value in fold_means) / len(fold_means), 6
            ) if fold_means else None,
            "monte_carlo_method": "moving_block_bootstrap",
            "monte_carlo_replicates": len(simulation),
            "monte_carlo_mean_p50_bps": round(_percentile(simulation, 0.50), 6) if simulation else None,
            "monte_carlo_p05_bps": round(_percentile(simulation, 0.05), 6) if simulation else None,
            "monte_carlo_p95_bps": round(_percentile(simulation, 0.95), 6) if simulation else None,
            "monte_carlo_probability_mean_positive": round(
                sum(value > 0.0 for value in simulation) / len(simulation), 6
            ) if simulation else None,
        })

    return {
        "schema_version": 1,
        "generated_at_ms": time.time_ns() // 1_000_000,
        "source": Path(outcomes_path).name,
        "raw_completed_paper_records": len(raw),
        "timestamped_valid_records": len(rows),
        "fold_count": len(folds),
        "train_size": train_size,
        "test_size": test_size,
        "step_size": step_size,
        "min_test_samples": min_test_samples,
        "scenario_count": len(scenario_reports),
        "scenarios": scenario_reports,
        "paper_only": True,
        "orders_submitted": False,
        "execution_authorized": False,
        "note": "Robustness evidence only. Extra-cost scenarios are stress assumptions applied after observed PAPER outcomes. Monte Carlo uses deterministic moving-block bootstrap of chronological OOS observations; it is not a forecast, profitability guarantee, or execution authorization.",
    }


def write_oos_robustness_report(
    outcomes_path: str | Path,
    report_path: str | Path,
    **kwargs: Any,
) -> dict[str, Any]:
    report = build_oos_robustness_report(outcomes_path, **kwargs)
    atomic_write_json(report_path, report)
    return report
