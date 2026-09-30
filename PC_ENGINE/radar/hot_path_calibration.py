# Path: PC_ENGINE/radar/hot_path_calibration.py
from __future__ import annotations

import hashlib
import json
import math
import random
import statistics
import time
from collections import defaultdict
from pathlib import Path
from typing import Any
from PC_ENGINE.radar.report_io import atomic_write_json


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read only completed, explicitly PAPER-only outcomes from the JSONL ledger."""
    rows: list[dict[str, Any]] = []
    try:
        with path.open("rb") as handle:
            for raw_line in handle:
                try:
                    value = json.loads(raw_line.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    continue
                if isinstance(value, dict) and value.get("status") == "COMPLETED" and value.get("paper_only") is True and value.get("orders_submitted") is False:
                    rows.append(value)
    except OSError:
        return []
    return rows


def _outcome_identity(row: dict[str, Any]) -> str:
    """Prefer a stable explicit ID; otherwise identify the same observed outcome."""
    explicit_id = row.get("outcome_id")
    if explicit_id is not None and str(explicit_id).strip():
        return "id:" + str(explicit_id).strip()
    fields = (
        "symbol", "leader", "follower", "direction", "horizon_ms",
        "leader_local_ts_ms", "entry_local_ts_ms", "outcome_local_ts_ms",
    )
    if all(row.get(field) is not None for field in fields):
        identity = {field: row[field] for field in fields}
    else:
        identity = row
    return json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _timestamped_values(values: list[float], rows: list[dict[str, Any]]) -> list[float]:
    timestamped: list[tuple[int, float]] = []
    now_ms = time.time_ns() // 1_000_000
    for row, value in zip(rows, values):
        try:
            timestamp = int(row["outcome_local_ts_ms"])
            if 0 < timestamp <= now_ms and math.isfinite(value):
                timestamped.append((timestamp, value))
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
    timestamped.sort(key=lambda item: item[0])
    return [value for _, value in timestamped]


def _temporal_dependence(values: list[float], rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Estimate first-order serial dependence and a conservative effective sample size."""
    ordered = _timestamped_values(values, rows)
    if len(ordered) < 3:
        return {
            "assessment": "UNAVAILABLE",
            "timestamped_samples": len(ordered),
            "lag1_autocorrelation": None,
            "effective_samples": len(values),
        }

    mean = statistics.fmean(ordered)
    centered = [value - mean for value in ordered]
    denominator = sum(value * value for value in centered)
    if denominator <= 0.0:
        rho = 0.0
    else:
        rho = sum(centered[i] * centered[i - 1] for i in range(1, len(centered))) / denominator
        rho = max(-0.999, min(0.999, rho))

    effective = len(ordered) * (1.0 - rho) / (1.0 + rho)
    effective = max(1.0, min(float(len(values)), effective))
    return {
        "assessment": "AVAILABLE",
        "timestamped_samples": len(ordered),
        "lag1_autocorrelation": round(rho, 6),
        "effective_samples": round(effective, 6),
    }


def _moving_block_bootstrap_ci(
    values: list[float],
    rows: list[dict[str, Any]],
    *,
    seed_key: str,
    replicates: int = 1000,
) -> dict[str, Any]:
    """Estimate a 95% mean CI with a deterministic moving-block bootstrap."""
    ordered = _timestamped_values(values, rows)
    n = len(ordered)
    if n < 8:
        return {
            "assessment": "UNAVAILABLE",
            "method": "effective_sample_normal",
            "bootstrap_replicates": 0,
            "block_length": None,
            "lower": None,
            "upper": None,
        }

    block_length = max(2, int(round(math.sqrt(n))))
    block_length = min(block_length, max(2, n // 2))
    seed = int.from_bytes(hashlib.sha256(seed_key.encode("utf-8")).digest()[:8], "big")
    rng = random.Random(seed)
    block_starts = list(range(n - block_length + 1))
    means: list[float] = []
    for _ in range(max(200, int(replicates))):
        sample: list[float] = []
        while len(sample) < n:
            start = rng.choice(block_starts)
            sample.extend(ordered[start:start + block_length])
        means.append(statistics.fmean(sample[:n]))

    means.sort()
    low_index = max(0, min(len(means) - 1, int(0.025 * (len(means) - 1))))
    high_index = max(0, min(len(means) - 1, int(0.975 * (len(means) - 1))))
    return {
        "assessment": "AVAILABLE",
        "method": "moving_block_bootstrap",
        "bootstrap_replicates": len(means),
        "block_length": block_length,
        "lower": means[low_index],
        "upper": means[high_index],
    }


def build_hot_path_calibration(
    outcomes_path: str | Path,
    *,
    min_samples: int = 100,
) -> dict[str, Any]:
    """Build a PAPER-only calibration report; never enables or authorizes execution."""
    path = Path(outcomes_path)
    min_samples = max(2, int(min_samples))
    raw_rows = _read_jsonl(path)
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    duplicate_outcomes_ignored = 0
    for row in raw_rows:
        # Invalid records must not reserve an identity: a later valid outcome with
        # the same ID/legacy identity still needs to be eligible for analysis.
        try:
            symbol = str(row["symbol"]).strip().upper()
            leader = str(row["leader"]).strip().lower()
            follower = str(row["follower"]).strip().lower()
            direction = str(row["direction"]).strip().upper()
            horizon = int(row["horizon_ms"])
            expected = float(row["expected_net_bps"])
            realized = float(row["realized_net_bps"])
            gross = float(row["realized_response_bps"])
            is_valid = bool(
                symbol and leader and follower
                and direction in {"UP", "DOWN"}
                and horizon > 0
                and all(math.isfinite(value) for value in (expected, realized, gross))
            )
        except (KeyError, TypeError, ValueError, OverflowError):
            is_valid = False

        if not is_valid:
            rows.append(row)
            continue

        identity = _outcome_identity(row)
        if identity in seen:
            duplicate_outcomes_ignored += 1
            continue
        seen.add(identity)
        rows.append(row)

    buckets: dict[tuple[str, str, str, str, int, str], list[dict[str, Any]]] = defaultdict(list)
    valid_outcome_samples = 0
    for row in rows:
        try:
            symbol = str(row["symbol"]).upper()
            leader = str(row["leader"]).lower()
            follower = str(row["follower"]).lower()
            direction = str(row["direction"]).upper()
            horizon = int(row["horizon_ms"])
            regime = str(row.get("market_regime", row.get("regime", "UNCLASSIFIED"))).strip().upper() or "UNCLASSIFIED"
            expected = float(row["expected_net_bps"])
            realized = float(row["realized_net_bps"])
            gross = float(row["realized_response_bps"])
            if not symbol or not leader or not follower or direction not in {"UP", "DOWN"}:
                continue
            if horizon <= 0 or not all(math.isfinite(v) for v in (expected, realized, gross)):
                continue
            buckets[(symbol, leader, follower, direction, horizon, regime)].append(row)
            valid_outcome_samples += 1
        except (KeyError, TypeError, ValueError, OverflowError):
            continue

    summaries: list[dict[str, Any]] = []
    for (symbol, leader, follower, direction, horizon, regime), group in sorted(buckets.items()):
        net = [float(row["realized_net_bps"]) for row in group]
        expected = [float(row["expected_net_bps"]) for row in group]
        gross = [float(row["realized_response_bps"]) for row in group]
        n = len(net)
        mean_net = statistics.fmean(net)
        std_net = statistics.stdev(net) if n > 1 else 0.0
        temporal = _temporal_dependence(net, group)
        ci_samples = float(temporal["effective_samples"])
        margin = 1.96 * std_net / math.sqrt(ci_samples) if ci_samples > 1.0 else float("inf")
        normal_lower = mean_net - margin if math.isfinite(margin) else None
        normal_upper = mean_net + margin if math.isfinite(margin) else None

        bootstrap = _moving_block_bootstrap_ci(
            net,
            group,
            seed_key=json.dumps(
                [symbol, leader, follower, direction, horizon, regime],
                ensure_ascii=False,
                separators=(",", ":"),
            ),
        )
        if bootstrap["assessment"] == "AVAILABLE":
            lower = bootstrap["lower"]
            upper = bootstrap["upper"]
            ci_method = bootstrap["method"]
        else:
            lower = normal_lower
            upper = normal_upper
            ci_method = "effective_sample_normal" if temporal["assessment"] == "AVAILABLE" else "sample_normal"

        mean_expected = statistics.fmean(expected)
        mean_gross = statistics.fmean(gross)
        summaries.append({
            "symbol": symbol,
            "leader": leader,
            "follower": follower,
            "direction": direction,
            "horizon_ms": horizon,
            "market_regime": regime,
            "samples": n,
            "profitable_after_costs_rate": round(sum(v > 0 for v in net) / n, 6),
            "mean_expected_net_bps": round(mean_expected, 6),
            "mean_realized_net_bps": round(mean_net, 6),
            "mean_realized_response_bps": round(mean_gross, 6),
            "mean_edge_error_bps": round(mean_net - mean_expected, 6),
            "net_stddev_bps": round(std_net, 6),
            "temporal_dependence_assessment": temporal["assessment"],
            "timestamped_samples": temporal["timestamped_samples"],
            "lag1_autocorrelation": temporal["lag1_autocorrelation"],
            "effective_samples": temporal["effective_samples"],
            "ci95_sample_basis": "effective_samples" if temporal["assessment"] == "AVAILABLE" else "samples",
            "ci95_method": ci_method,
            "bootstrap_replicates": bootstrap["bootstrap_replicates"],
            "bootstrap_block_length": bootstrap["block_length"],
            "net_ci95_lower_bps": round(lower, 6) if lower is not None else None,
            "net_ci95_upper_bps": round(upper, 6) if upper is not None else None,
            "eligible_for_paper_review": bool(
                n >= min_samples
                and ci_samples >= min_samples
                and lower is not None
                and lower > 0.0
            ),
        })

    return {
        "schema_version": 3,
        "generated_at_ms": time.time_ns() // 1_000_000,
        "source": path.name,
        "outcome_records_loaded": len(raw_rows),
        "unique_completed_paper_records": len(rows),
        "outcome_samples": valid_outcome_samples,
        "duplicate_outcomes_ignored": duplicate_outcomes_ignored,
        "invalid_outcomes_ignored": len(rows) - valid_outcome_samples,
        "relationships": len(summaries),
        "min_samples": min_samples,
        "paper_only": True,
        "orders_submitted": False,
        "execution_authorized": False,
        "note": "Calibration evidence only; duplicate and invalid outcomes are excluded from samples. Timestamped outcomes use first-order serial-dependence adjustment plus deterministic moving-block bootstrap confidence intervals when enough temporal data exists; eligibility is not execution authorization.",
        "stats": summaries,
    }


def write_hot_path_calibration(
    outcomes_path: str | Path,
    report_path: str | Path,
    *,
    min_samples: int = 100,
) -> dict[str, Any]:
    report = build_hot_path_calibration(outcomes_path, min_samples=min_samples)
    atomic_write_json(report_path, report)
    return report
