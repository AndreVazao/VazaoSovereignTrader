from __future__ import annotations

import json
import math
import statistics
from pathlib import Path
from typing import Any


def _read_rows(path: Path) -> list[dict[str, Any]]:
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


def _timestamp(row: dict[str, Any]) -> int | None:
    try:
        value = int(row["outcome_local_ts_ms"])
        return value if value > 0 else None
    except (KeyError, TypeError, ValueError, OverflowError):
        return None


def _valid(row: dict[str, Any]) -> bool:
    try:
        values = (
            float(row["expected_net_bps"]),
            float(row["realized_net_bps"]),
            float(row["realized_response_bps"]),
        )
        return (
            str(row.get("direction", "")).upper() in {"UP", "DOWN"}
            and int(row["horizon_ms"]) > 0
            and all(math.isfinite(value) for value in values)
            and _timestamp(row) is not None
        )
    except (KeyError, TypeError, ValueError, OverflowError):
        return False


def _identity(row: dict[str, Any]) -> str:
    explicit = row.get("outcome_id")
    if explicit is not None and str(explicit).strip():
        return "id:" + str(explicit).strip()
    fields = (
        "symbol", "leader", "follower", "direction", "horizon_ms",
        "leader_local_ts_ms", "entry_local_ts_ms", "outcome_local_ts_ms",
    )
    if all(row.get(field) is not None for field in fields):
        return json.dumps({field: row[field] for field in fields}, sort_keys=True, separators=(",", ":"), default=str)
    return json.dumps(row, sort_keys=True, separators=(",", ":"), default=str)


def _mean(values: list[float]) -> float | None:
    return statistics.fmean(values) if values else None


def _folds(rows: list[dict[str, Any]], train_size: int, test_size: int, step: int) -> list[dict[str, Any]]:
    ordered = sorted(rows, key=lambda row: int(row["outcome_local_ts_ms"]))
    result = []
    start = 0
    while start + train_size + test_size <= len(ordered):
        train = ordered[start:start + train_size]
        test = ordered[start + train_size:start + train_size + test_size]
        train_net = [float(row["realized_net_bps"]) for row in train]
        train_expected = [float(row["expected_net_bps"]) for row in train]
        test_net = [float(row["realized_net_bps"]) for row in test]
        test_expected = [float(row["expected_net_bps"]) for row in test]

        train_mean = _mean(train_net)
        test_mean = _mean(test_net)
        test_std = statistics.stdev(test_net) if len(test_net) > 1 else 0.0
        result.append({
            "train_start_ts_ms": int(train[0]["outcome_local_ts_ms"]),
            "train_end_ts_ms": int(train[-1]["outcome_local_ts_ms"]),
            "test_start_ts_ms": int(test[0]["outcome_local_ts_ms"]),
            "test_end_ts_ms": int(test[-1]["outcome_local_ts_ms"]),
            "train_samples": len(train),
            "test_samples": len(test),
            "train_mean_realized_net_bps": round(train_mean, 6) if train_mean is not None else None,
            "train_mean_expected_net_bps": round(_mean(train_expected), 6),
            "test_mean_realized_net_bps": round(test_mean, 6),
            "test_mean_expected_net_bps": round(_mean(test_expected), 6),
            "test_profitable_after_costs_rate": round(sum(value > 0 for value in test_net) / len(test_net), 6),
            "test_net_stddev_bps": round(test_std, 6),
            "test_passes_train_sign_gate": bool(train_mean is not None and train_mean > 0 and test_mean is not None and test_mean > 0),
            "test_observed_edge_error_bps": round(test_mean - _mean(test_expected), 6),
        })
        start += step
    return result


def build_walk_forward_report(
    outcomes_path: str | Path,
    *,
    train_size: int = 100,
    test_size: int = 50,
    step: int = 50,
    min_test_samples: int = 30,
) -> dict[str, Any]:
    """Produce a chronological PAPER-only walk-forward evidence report.

    Training data is used only to establish the sign gate; test rows are strictly
    later observations and are never used to form the training estimate.
    """
    path = Path(outcomes_path)
    train_size = max(2, int(train_size))
    test_size = max(2, int(test_size))
    step = max(1, int(step))
    min_test_samples = max(2, int(min_test_samples))

    raw = _read_rows(path)
    seen: set[str] = set()
    rows: list[dict[str, Any]] = []
    duplicates = 0
    invalid = 0
    for row in raw:
        identity = _identity(row)
        if identity in seen:
            duplicates += 1
            continue
        seen.add(identity)
        if not _valid(row):
            invalid += 1
            continue
        rows.append(row)

    groups: dict[tuple[str, str, str, str, int, str], list[dict[str, Any]]] = {}
    for row in rows:
        key = (
            str(row["symbol"]).upper(),
            str(row["leader"]).lower(),
            str(row["follower"]).lower(),
            str(row["direction"]).upper(),
            int(row["horizon_ms"]),
            str(row.get("market_regime", row.get("regime", "UNCLASSIFIED"))).strip().upper() or "UNCLASSIFIED",
        )
        groups.setdefault(key, []).append(row)

    summaries = []
    for key, group in sorted(groups.items()):
        group = sorted(group, key=lambda row: int(row["outcome_local_ts_ms"]))
        folds = _folds(group, train_size, test_size, step)
        usable = [fold for fold in folds if fold["test_samples"] >= min_test_samples]
        passed = [fold for fold in usable if fold["test_passes_train_sign_gate"]]
        summaries.append({
            "symbol": key[0],
            "leader": key[1],
            "follower": key[2],
            "direction": key[3],
            "horizon_ms": key[4],
            "market_regime": key[5],
            "samples": len(group),
            "folds": len(folds),
            "usable_folds": len(usable),
            "test_positive_after_train_sign_rate": round(len(passed) / len(usable), 6) if usable else None,
            "mean_test_net_bps": round(_mean([fold["test_mean_realized_net_bps"] for fold in usable]), 6) if usable else None,
            "mean_test_edge_error_bps": round(_mean([fold["test_observed_edge_error_bps"] for fold in usable]), 6) if usable else None,
            "walk_forward_evidence_available": bool(usable),
            "folds_detail": usable,
        })

    return {
        "schema_version": 1,
        "generated_at_ms": __import__("time").time_ns() // 1_000_000,
        "source": path.name,
        "outcome_records_loaded": len(raw),
        "unique_completed_paper_records": len(raw) - duplicates,
        "valid_timestamped_samples": len(rows),
        "duplicate_outcomes_ignored": duplicates,
        "invalid_or_untimestamped_ignored": invalid,
        "train_size": train_size,
        "test_size": test_size,
        "step": step,
        "min_test_samples": min_test_samples,
        "paper_only": True,
        "orders_submitted": False,
        "execution_authorized": False,
        "note": "Chronological evidence only. Each test window is strictly later than its training window; the report does not authorize execution.",
        "stats": summaries,
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
