# Path: PC_ENGINE/radar/hot_path_relationship_oos.py
from __future__ import annotations

import json
import math
import statistics
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

from PC_ENGINE.radar.report_io import atomic_write_json


_IDENTITY_FIELDS = (
    "symbol",
    "leader",
    "follower",
    "direction",
    "horizon_ms",
    "leader_local_ts_ms",
    "entry_local_ts_ms",
    "outcome_local_ts_ms",
)


def _identity(row: dict[str, Any]) -> str:
    explicit = row.get("outcome_id")
    if explicit is not None and str(explicit).strip():
        return "id:" + str(explicit).strip()
    return json.dumps(
        {key: row.get(key) for key in _IDENTITY_FIELDS},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def _finite(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def _read_valid_outcomes(
    path: Path,
    *,
    max_records: int,
    now_ms: int,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    counters = {
        "raw_lines_seen": 0,
        "malformed_lines_ignored": 0,
        "non_paper_records_ignored": 0,
        "invalid_outcomes_ignored": 0,
        "duplicate_outcomes_ignored": 0,
        "valid_unique_outcomes": 0,
        "records_omitted_by_limit": 0,
    }
    rows: deque[dict[str, Any]] = deque(maxlen=max(1, int(max_records)))
    try:
        handle = path.open("rb")
    except OSError:
        return [], counters

    with handle:
        for raw_line in handle:
            if not raw_line.strip():
                continue
            counters["raw_lines_seen"] += 1
            try:
                row = json.loads(raw_line.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                counters["malformed_lines_ignored"] += 1
                continue
            if not isinstance(row, dict):
                counters["invalid_outcomes_ignored"] += 1
                continue
            if (
                row.get("status") != "COMPLETED"
                or row.get("paper_only") is not True
                or row.get("orders_submitted") is not False
            ):
                counters["non_paper_records_ignored"] += 1
                continue

            try:
                symbol = str(row["symbol"]).strip().upper()
                leader = str(row["leader"]).strip().lower()
                follower = str(row["follower"]).strip().lower()
                direction = str(row["direction"]).strip().upper()
                horizon_ms = int(row["horizon_ms"])
                timestamp_ms = int(row["outcome_local_ts_ms"])
                expected = _finite(row["expected_net_bps"])
                realized = _finite(row["realized_net_bps"])
                if (
                    not symbol
                    or not leader
                    or not follower
                    or direction not in {"UP", "DOWN"}
                    or horizon_ms <= 0
                    or timestamp_ms <= 0
                    or timestamp_ms > now_ms
                    or expected is None
                    or realized is None
                ):
                    raise ValueError("invalid outcome fields")
            except (KeyError, TypeError, ValueError, OverflowError):
                counters["invalid_outcomes_ignored"] += 1
                continue

            # Invalid records never reserve an identity. Only validated outcomes
            # participate in deduplication, preventing an invalid first row from
            # suppressing a later valid row with the same outcome_id.
            identity = _identity(row)
            if any(existing["_identity"] == identity for existing in rows):
                counters["duplicate_outcomes_ignored"] += 1
                continue

            normalized = {
                **row,
                "_identity": identity,
                "symbol": symbol,
                "leader": leader,
                "follower": follower,
                "direction": direction,
                "horizon_ms": horizon_ms,
                "outcome_local_ts_ms": timestamp_ms,
                "expected_net_bps": expected,
                "realized_net_bps": realized,
                "market_regime": str(
                    row.get("market_regime", row.get("regime", "UNCLASSIFIED"))
                ).strip().upper() or "UNCLASSIFIED",
            }
            if len(rows) == rows.maxlen:
                counters["records_omitted_by_limit"] += 1
            rows.append(normalized)

    counters["valid_unique_outcomes"] = len(rows)
    # The bounded reader retains the most recent records; return them chronologically.
    return sorted(rows, key=lambda row: int(row["outcome_local_ts_ms"])), counters


def _mean_ci(values: list[float]) -> tuple[float | None, float | None]:
    if len(values) < 2:
        return None, None
    mean = statistics.fmean(values)
    margin = 1.96 * statistics.stdev(values) / math.sqrt(len(values))
    return mean - margin, mean + margin


def build_relationship_oos_report(
    outcomes_path: str | Path,
    *,
    min_samples: int = 100,
    min_test_samples: int = 20,
    train_fraction: float = 0.7,
    max_records: int = 100_000,
    now_ms: int | None = None,
) -> dict[str, Any]:
    """Build per-relationship chronological holdout evidence from completed PAPER outcomes."""
    min_samples = max(2, int(min_samples))
    min_test_samples = max(1, int(min_test_samples))
    try:
        fraction = float(train_fraction)
    except (TypeError, ValueError, OverflowError):
        fraction = 0.7
    if not math.isfinite(fraction) or fraction < 0.5 or fraction > 0.9:
        fraction = 0.7

    path = Path(outcomes_path)
    now = int(now_ms if now_ms is not None else time.time_ns() // 1_000_000)
    rows, counters = _read_valid_outcomes(path, max_records=max_records, now_ms=now)
    groups: dict[tuple[str, str, str, str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(
            row["symbol"], row["leader"], row["follower"],
            row["direction"], row["horizon_ms"],
        )].append(row)

    relationships: list[dict[str, Any]] = []
    for key, group in sorted(groups.items()):
        group.sort(key=lambda row: int(row["outcome_local_ts_ms"]))
        count = len(group)
        split = max(1, min(count - 1, int(math.floor(count * fraction)))) if count >= 2 else count
        train = group[:split]
        test = group[split:]
        train_values = [float(row["realized_net_bps"]) for row in train]
        test_values = [float(row["realized_net_bps"]) for row in test]
        train_mean = statistics.fmean(train_values) if train_values else None
        test_mean = statistics.fmean(test_values) if test_values else None
        lower, upper = _mean_ci(test_values)
        enough = count >= min_samples and len(test) >= min_test_samples
        supported = bool(enough and lower is not None and lower > 0.0)
        relationships.append({
            "symbol": key[0],
            "leader": key[1],
            "follower": key[2],
            "direction": key[3],
            "horizon_ms": key[4],
            "samples": count,
            "train_samples": len(train),
            "test_samples": len(test),
            "train_start_ms": int(train[0]["outcome_local_ts_ms"]) if train else None,
            "train_end_ms": int(train[-1]["outcome_local_ts_ms"]) if train else None,
            "test_start_ms": int(test[0]["outcome_local_ts_ms"]) if test else None,
            "test_end_ms": int(test[-1]["outcome_local_ts_ms"]) if test else None,
            "train_mean_net_bps": round(train_mean, 6) if train_mean is not None else None,
            "oos_mean_net_bps": round(test_mean, 6) if test_mean is not None else None,
            "oos_median_net_bps": round(statistics.median(test_values), 6) if test_values else None,
            "oos_positive_rate": round(sum(value > 0 for value in test_values) / len(test_values), 6) if test_values else None,
            "oos_ci95_lower_bps": round(lower, 6) if lower is not None else None,
            "oos_ci95_upper_bps": round(upper, 6) if upper is not None else None,
            "sample_sufficiency": "SUFFICIENT" if enough else "INSUFFICIENT",
            "oos_edge_supported": supported,
            "eligible_for_paper_review": supported,
        })

    return {
        "schema_version": 1,
        "generated_at_ms": now,
        "source": path.name,
        "source_exists": path.is_file(),
        "raw_lines_seen": counters["raw_lines_seen"],
        "valid_unique_outcomes": counters["valid_unique_outcomes"],
        "malformed_lines_ignored": counters["malformed_lines_ignored"],
        "non_paper_records_ignored": counters["non_paper_records_ignored"],
        "invalid_outcomes_ignored": counters["invalid_outcomes_ignored"],
        "duplicate_outcomes_ignored": counters["duplicate_outcomes_ignored"],
        "records_omitted_by_limit": counters["records_omitted_by_limit"],
        "relationships": len(relationships),
        "min_samples": min_samples,
        "min_test_samples": min_test_samples,
        "train_fraction": fraction,
        "eligible_relationships_for_paper_review": sum(
            1 for row in relationships if row["eligible_for_paper_review"]
        ),
        "paper_only": True,
        "orders_submitted": False,
        "execution_authorized": False,
        "note": "Per-relationship chronological holdout diagnostics only. The test window follows the training window; insufficient evidence is ineligible. A positive lower confidence bound is only a candidate for PAPER review and never authorizes REAL execution or establishes future profitability.",
        "relationship_details": relationships,
    }


def write_relationship_oos_report(
    outcomes_path: str | Path,
    report_path: str | Path,
    **kwargs: Any,
) -> dict[str, Any]:
    report = build_relationship_oos_report(outcomes_path, **kwargs)
    atomic_write_json(report_path, report)
    return report
