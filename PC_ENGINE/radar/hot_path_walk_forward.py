from __future__ import annotations

import json
import math
import statistics
from pathlib import Path
from typing import Any


def _read_completed_paper(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if (
                isinstance(row, dict)
                and row.get("status") == "COMPLETED"
                and row.get("paper_only") is True
                and row.get("orders_submitted") is False
            ):
                rows.append(row)
    except OSError:
        return []
    return rows


def _valid_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    valid: list[dict[str, Any]] = []
    for row in rows:
        try:
            identity = str(row.get("outcome_id") or json.dumps(
                {
                    key: row.get(key)
                    for key in (
                        "symbol", "leader", "follower", "direction", "horizon_ms",
                        "leader_local_ts_ms", "entry_local_ts_ms", "outcome_local_ts_ms",
                    )
                },
                sort_keys=True,
                default=str,
            ))
            timestamp = int(row["outcome_local_ts_ms"])
            realized = float(row["realized_net_bps"])
            expected = float(row["expected_net_bps"])
            regime = str(row.get("market_regime", row.get("regime", "UNCLASSIFIED"))).strip().upper() or "UNCLASSIFIED"
            if timestamp <= 0 or not all(math.isfinite(value) for value in (realized, expected)):
                continue
            if identity in seen:
                continue
            seen.add(identity)
            valid.append({
                **row,
                "outcome_local_ts_ms": timestamp,
                "realized_net_bps": realized,
                "expected_net_bps": expected,
                "market_regime": regime,
            })
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
    return sorted(valid, key=lambda row: int(row["outcome_local_ts_ms"]))


def _normal_ci(values: list[float]) -> tuple[float | None, float | None]:
    if len(values) < 2:
        return None, None
    mean = statistics.fmean(values)
    std = statistics.stdev(values)
    margin = 1.96 * std / math.sqrt(len(values))
    return mean - margin, mean + margin


def build_walk_forward_report(
    outcomes_path: str | Path,
    *,
    train_size: int = 100,
    test_size: int = 25,
    step_size: int | None = None,
    min_test_samples: int = 10,
) -> dict[str, Any]:
    """Build chronological PAPER-only walk-forward evidence without optimizing execution."""
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

        train_net = [float(row["realized_net_bps"]) for row in train]
        test_net = [float(row["realized_net_bps"]) for row in test]
        train_mean = statistics.fmean(train_net) if train_net else None
        test_mean = statistics.fmean(test_net)
        lower, upper = _normal_ci(test_net)
        folds.append({
            "fold": len(folds) + 1,
            "train_samples": len(train),
            "test_samples": len(test),
            "train_start_ms": int(train[0]["outcome_local_ts_ms"]) if train else None,
            "train_end_ms": int(train[-1]["outcome_local_ts_ms"]) if train else None,
            "test_start_ms": int(test[0]["outcome_local_ts_ms"]),
            "test_end_ms": int(test[-1]["outcome_local_ts_ms"]),
            "train_mean_realized_net_bps": round(train_mean, 6) if train_mean is not None else None,
            "test_mean_realized_net_bps": round(test_mean, 6),
            "test_profitable_after_costs_rate": round(sum(value > 0 for value in test_net) / len(test_net), 6),
            "test_ci95_lower_bps": round(lower, 6) if lower is not None else None,
            "test_ci95_upper_bps": round(upper, 6) if upper is not None else None,
            "train_positive": bool(train_mean is not None and train_mean > 0),
            "test_positive": bool(test_mean > 0),
        })
        start += step_size

    positive_test_folds = sum(fold["test_positive"] for fold in folds)
    return {
        "schema_version": 1,
        "generated_at_ms": __import__("time").time_ns() // 1_000_000,
        "source": Path(outcomes_path).name,
        "raw_completed_paper_records": len(raw),
        "timestamped_valid_records": len(rows),
        "train_size": train_size,
        "test_size": test_size,
        "step_size": step_size,
        "min_test_samples": min_test_samples,
        "folds": folds,
        "fold_count": len(folds),
        "positive_test_fold_rate": round(positive_test_folds / len(folds), 6) if folds else None,
        "paper_only": True,
        "orders_submitted": False,
        "execution_authorized": False,
        "note": "Chronological evidence report only. Each test window follows its training window and is not used to select parameters. This is a walk-forward evidence check, not proof of future profitability or an execution authorization.",
    }


def write_walk_forward_report(
    outcomes_path: str | Path,
    report_path: str | Path,
    **kwargs: Any,
) -> dict[str, Any]:
    report = build_walk_forward_report(outcomes_path, **kwargs)
    destination = Path(report_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2), encoding="utf-8")
    temporary.replace(destination)
    return report
