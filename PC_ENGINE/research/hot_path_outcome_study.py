# Path: PC_ENGINE/research/hot_path_outcome_study.py
from __future__ import annotations

import json
import math
from collections import defaultdict, deque
from pathlib import Path
from typing import Any


def load_hot_path_outcomes(path: str | Path, *, limit: int = 100_000) -> tuple[list[dict[str, Any]], int]:
    """Load the most recent JSONL outcomes with bounded memory; count malformed rows."""
    source = Path(path)
    if not source.exists():
        return [], 0
    rows: deque[dict[str, Any]] = deque(maxlen=max(1, int(limit)))
    invalid = 0
    with source.open("r", encoding="utf-8") as handle:
        for line in handle:
            raw = line.strip()
            if not raw:
                continue
            try:
                value = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                invalid += 1
                continue
            if not isinstance(value, dict):
                invalid += 1
                continue
            rows.append(value)
    return list(rows), invalid


def _finite(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _summary(values: list[float]) -> dict[str, float | int]:
    count = len(values)
    if count == 0:
        return {"samples": 0, "mean_net_bps": 0.0, "median_net_bps": 0.0, "win_rate": 0.0, "lower_95ci_net_bps": 0.0}
    ordered = sorted(values)
    mean = sum(values) / count
    median = ordered[count // 2] if count % 2 else (ordered[count // 2 - 1] + ordered[count // 2]) / 2.0
    variance = sum((value - mean) ** 2 for value in values) / max(1, count - 1)
    standard_error = math.sqrt(variance / count)
    return {
        "samples": count,
        "mean_net_bps": round(mean, 6),
        "median_net_bps": round(median, 6),
        "win_rate": round(sum(value > 0 for value in values) / count, 6),
        "lower_95ci_net_bps": round(mean - 1.96 * standard_error, 6),
    }


def run_hot_path_outcome_study(
    rows: list[dict[str, Any]],
    *,
    invalid_records: int = 0,
    min_samples: int = 100,
    min_test_samples: int = 20,
    train_fraction: float = 0.7,
    min_test_net_bps: float = 0.0,
) -> dict[str, Any]:
    """Chronological OOS summary. Eligibility is research-only, never REAL authorization."""
    fraction = min(0.9, max(0.5, float(train_fraction)))
    grouped: dict[tuple[str, str, str, str], list[tuple[int, dict[str, Any], float]]] = defaultdict(list)
    valid_records = 0
    rejected_records = 0

    for index, row in enumerate(rows):
        if (
            row.get("status") != "COMPLETED"
            or row.get("paper_only") is not True
            or row.get("orders_submitted") is not False
        ):
            rejected_records += 1
            continue
        net = _finite(row.get("realized_net_bps"))
        timestamp = _finite(row.get("outcome_local_ts_ms"))
        symbol = str(row.get("symbol") or "").upper()
        leader = str(row.get("leader") or "").lower()
        follower = str(row.get("follower") or "").lower()
        direction = str(row.get("direction") or "").upper()
        if net is None or timestamp is None or not symbol or not leader or not follower or direction not in {"UP", "DOWN"}:
            rejected_records += 1
            continue
        valid_records += 1
        grouped[(symbol, leader, follower, direction)].append((int(timestamp), row, net))

    relationships = []
    for key, samples in sorted(grouped.items()):
        samples.sort(key=lambda item: item[0])
        count = len(samples)
        train_count = int(count * fraction)
        test = samples[train_count:]
        train_values = [item[2] for item in samples[:train_count]]
        test_values = [item[2] for item in test]
        train_summary = _summary(train_values)
        test_summary = _summary(test_values)
        enough = count >= max(1, int(min_samples)) and len(test_values) >= max(1, int(min_test_samples))
        lower_ci = float(test_summary["lower_95ci_net_bps"])
        eligible = enough and float(test_summary["mean_net_bps"]) > float(min_test_net_bps) and lower_ci > float(min_test_net_bps)
        cumulative = 0.0
        peak = 0.0
        max_drawdown = 0.0
        for value in test_values:
            cumulative += value
            peak = max(peak, cumulative)
            max_drawdown = max(max_drawdown, peak - cumulative)
        relationships.append({
            "symbol": key[0],
            "leader": key[1],
            "follower": key[2],
            "direction": key[3],
            "samples": count,
            "train_samples": len(train_values),
            "test_samples": len(test_values),
            "train": train_summary,
            "test": test_summary,
            "test_max_drawdown_bps": round(max_drawdown, 6),
            "eligible_for_oos_review": bool(eligible),
            "status": "OOS_EDGE_CANDIDATE" if eligible else ("INSUFFICIENT_EVIDENCE" if not enough else "OOS_EDGE_NOT_CONFIRMED"),
        })

    eligible_count = sum(1 for row in relationships if row["eligible_for_oos_review"])
    return {
        "schema_version": 1,
        "study": "hot_path_lead_lag_outcomes",
        "paper_only": True,
        "orders_submitted": False,
        "real_authorization_changed": False,
        "status": "OOS_EDGE_CANDIDATES_FOUND" if eligible_count else ("INSUFFICIENT_EVIDENCE" if not valid_records else "NO_OOS_EDGE_CONFIRMED"),
        "input_records": len(rows),
        "valid_records": valid_records,
        "invalid_json_records": max(0, int(invalid_records)),
        "rejected_records": rejected_records,
        "relationships": len(relationships),
        "eligible_relationships": eligible_count,
        "min_samples": max(1, int(min_samples)),
        "min_test_samples": max(1, int(min_test_samples)),
        "train_fraction": fraction,
        "min_test_net_bps": float(min_test_net_bps),
        "relationships_detail": relationships,
        "warning": "OOS eligibility is research evidence only and never authorizes REAL execution.",
    }


def write_hot_path_outcome_study(report: dict[str, Any], path: str | Path) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2), encoding="utf-8")
    temporary.replace(destination)
