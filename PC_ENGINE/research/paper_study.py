from __future__ import annotations

from bisect import bisect_left
import json
import math
import random
from pathlib import Path
from statistics import mean, median
from typing import Any


def load_states(path: str | Path, limit: int = 100_000) -> list[dict[str, Any]]:
    target = Path(path)
    if not target.exists():
        return []
    rows: list[dict[str, Any]] = []
    with target.open("rb") as handle:
        raw_rows = handle.readlines()[-max(1, int(limit)):]
    for raw in raw_rows:
        try:
            row = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        if (
            isinstance(row, dict)
            and str(row.get("symbol", ""))
            and int(row.get("timestamp_ms", 0)) > 0
            and float(row.get("price", 0)) > 0
            and str(row.get("action", "")).upper() in {"BUY", "SELL"}
        ):
            rows.append(row)
    return sorted(rows, key=lambda row: (int(row["timestamp_ms"]), str(row["symbol"])))


def _future_index(states: list[dict[str, Any]]) -> dict[str, tuple[list[int], list[float]]]:
    grouped: dict[str, list[tuple[int, float]]] = {}
    for row in states:
        grouped.setdefault(str(row["symbol"]), []).append((int(row["timestamp_ms"]), float(row["price"])))
    return {
        symbol: (
            [item[0] for item in ordered],
            [item[1] for item in ordered],
        )
        for symbol, values in grouped.items()
        for ordered in [sorted(values)]
    }


def simulate(states: list[dict[str, Any]], *, horizon_ms: int, cost_bps: float, min_confluence: float = -1.0, min_confidence: float = 0.0) -> list[dict[str, Any]]:
    index = _future_index(states)
    outcomes: list[dict[str, Any]] = []
    for row in states:
        action = str(row["action"]).upper()
        confluence = abs(float(row.get("confluence_score", 0.0)))
        confidence = float(row.get("confluence_confidence", 0.0))
        if confluence < float(min_confluence) or confidence < float(min_confidence):
            continue
        timestamps, prices = index.get(str(row["symbol"]), ([], []))
        if not timestamps:
            continue
        target = int(row["timestamp_ms"]) + int(horizon_ms)
        pos = bisect_left(timestamps, target)
        if pos >= len(timestamps):
            continue
        p0 = float(row["price"])
        p1 = float(prices[pos])
        gross_bps = ((p1 / p0) - 1.0) * 10000.0
        signed_bps = gross_bps if action == "BUY" else -gross_bps
        net_bps = signed_bps - float(cost_bps)
        outcomes.append({
            "timestamp_ms": int(row["timestamp_ms"]),
            "symbol": str(row["symbol"]),
            "regime": str(row.get("regime", "UNKNOWN")),
            "action": action,
            "confluence_score": float(row.get("confluence_score", 0.0)),
            "confluence_confidence": confidence,
            "net_bps": net_bps,
        })
    return outcomes


def _summary(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"samples": 0, "wins": 0, "win_rate": 0.0, "mean_net_bps": 0.0, "median_net_bps": 0.0, "p05_net_bps": 0.0, "p95_net_bps": 0.0}
    ordered = sorted(values)
    def pct(p: float) -> float:
        index = (len(ordered) - 1) * p
        lo = int(index)
        hi = min(lo + 1, len(ordered) - 1)
        frac = index - lo
        return ordered[lo] + (ordered[hi] - ordered[lo]) * frac
    return {
        "samples": len(values),
        "wins": sum(1 for value in values if value > 0),
        "win_rate": sum(1 for value in values if value > 0) / len(values),
        "mean_net_bps": mean(values),
        "median_net_bps": median(values),
        "p05_net_bps": pct(0.05),
        "p95_net_bps": pct(0.95),
    }


def chronological_split(rows: list[dict[str, Any]], train_ratio: float = 0.7) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    ordered = sorted(rows, key=lambda row: int(row["timestamp_ms"]))
    cut = max(1, min(len(ordered) - 1, int(len(ordered) * float(train_ratio)))) if len(ordered) > 1 else len(ordered)
    return ordered[:cut], ordered[cut:]


def walk_forward(rows: list[dict[str, Any]], *, folds: int = 5, min_train: int = 100, test_size: int = 50) -> list[dict[str, Any]]:
    ordered = sorted(rows, key=lambda row: int(row["timestamp_ms"]))
    if len(ordered) < min_train + test_size:
        return []
    available = len(ordered) - min_train
    step = max(1, available // max(1, int(folds)))
    reports: list[dict[str, Any]] = []
    for fold in range(max(1, int(folds))):
        train_end = min(len(ordered) - test_size, min_train + fold * step)
        test_end = min(len(ordered), train_end + test_size)
        if train_end < min_train or test_end <= train_end:
            break
        train = ordered[:train_end]
        test = ordered[train_end:test_end]
        reports.append({
            "fold": fold + 1,
            "train_samples": len(train),
            "test_samples": len(test),
            "train_summary": _summary([float(row["net_bps"]) for row in train]),
            "test_summary": _summary([float(row["net_bps"]) for row in test]),
            "test_start_ms": int(test[0]["timestamp_ms"]),
            "test_end_ms": int(test[-1]["timestamp_ms"]),
        })
    return reports


def regime_breakdown(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    groups: dict[str, list[float]] = {}
    for row in rows:
        groups.setdefault(str(row.get("regime", "UNKNOWN")), []).append(float(row["net_bps"]))
    return {regime: _summary(values) for regime, values in sorted(groups.items())}


def monte_carlo(rows: list[dict[str, Any]], *, iterations: int = 2000, sample_size: int | None = None, seed: int = 42) -> dict[str, Any]:
    values = [float(row["net_bps"]) for row in rows]
    if not values:
        return {"iterations": 0, "sample_size": 0, "seed": seed, "mean_net_bps_distribution": [], "probability_mean_leq_zero": 1.0}
    size = max(1, min(len(values), int(sample_size or len(values))))
    rng = random.Random(seed)
    means: list[float] = []
    for _ in range(max(1, int(iterations))):
        sample = [values[rng.randrange(len(values))] for _ in range(size)]
        means.append(mean(sample))
    non_positive = sum(1 for value in means if value <= 0)
    return {
        "iterations": len(means),
        "sample_size": size,
        "seed": seed,
        "mean_net_bps_distribution": _summary(means),
        "probability_mean_leq_zero": non_positive / len(means),
    }


def compare_paper_policies(states: list[dict[str, Any]], *, horizon_ms: int, cost_bps: float, high_confidence: float = 0.70, high_confluence: float = 0.30) -> dict[str, Any]:
    signal = simulate(states, horizon_ms=horizon_ms, cost_bps=cost_bps)
    filtered = simulate(states, horizon_ms=horizon_ms, cost_bps=cost_bps, min_confluence=high_confluence, min_confidence=high_confidence)
    return {
        "signal": _summary([row["net_bps"] for row in signal]),
        "high_confidence": _summary([row["net_bps"] for row in filtered]),
        "policy_parameters": {
            "high_confidence": float(high_confidence),
            "high_confluence": float(high_confluence),
        },
    }


def run_study(
    states: list[dict[str, Any]],
    *,
    horizon_ms: int = 5000,
    cost_bps: float = 28.0,
    folds: int = 5,
    min_train: int = 100,
    test_size: int = 50,
    monte_carlo_iterations: int = 2000,
) -> dict[str, Any]:
    outcomes = simulate(states, horizon_ms=horizon_ms, cost_bps=cost_bps)
    train, test = chronological_split(outcomes)
    report = {
        "schema_version": 1,
        "paper_only": True,
        "orders_submitted": False,
        "horizon_ms": int(horizon_ms),
        "cost_bps": float(cost_bps),
        "source_samples": len(states),
        "outcome_samples": len(outcomes),
        "overall": _summary([row["net_bps"] for row in outcomes]),
        "chronological_oos": {
            "train": _summary([row["net_bps"] for row in train]),
            "test": _summary([row["net_bps"] for row in test]),
        },
        "walk_forward": walk_forward(outcomes, folds=folds, min_train=min_train, test_size=test_size),
        "regimes": regime_breakdown(outcomes),
        "monte_carlo": monte_carlo(outcomes, iterations=monte_carlo_iterations),
        "policy_comparison": compare_paper_policies(states, horizon_ms=horizon_ms, cost_bps=cost_bps),
    }
    return report


def write_report(report: dict[str, Any], path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
