# Path: PC_ENGINE/radar/hot_path_calibration.py
from __future__ import annotations

import json
import math
import statistics
import time
from collections import defaultdict
from pathlib import Path
from typing import Any


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read only completed, explicitly PAPER-only outcomes from the JSONL ledger."""
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    value = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if (
                    isinstance(value, dict)
                    and value.get("status") == "COMPLETED"
                    and value.get("paper_only") is True
                    and value.get("orders_submitted") is False
                ):
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
        # Legacy records without timestamps can only be deduplicated if their
        # complete serialized contents are identical.
        identity = row
    return json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


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
        identity = _outcome_identity(row)
        if identity in seen:
            duplicate_outcomes_ignored += 1
            continue
        seen.add(identity)
        rows.append(row)

    buckets: dict[tuple[str, str, str, str, int, str], list[dict[str, Any]]] = defaultdict(list)
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
        margin = 1.96 * std_net / math.sqrt(n) if n > 1 else float("inf")
        lower = mean_net - margin if math.isfinite(margin) else None
        upper = mean_net + margin if math.isfinite(margin) else None
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
            "net_ci95_lower_bps": round(lower, 6) if lower is not None else None,
            "net_ci95_upper_bps": round(upper, 6) if upper is not None else None,
            "eligible_for_paper_review": bool(n >= min_samples and lower is not None and lower > 0.0),
        })

    return {
        "schema_version": 1,
        "generated_at_ms": time.time_ns() // 1_000_000,
        "source": path.name,
        "outcome_samples": len(rows),
        "duplicate_outcomes_ignored": duplicate_outcomes_ignored,
        "relationships": len(summaries),
        "min_samples": min_samples,
        "paper_only": True,
        "orders_submitted": False,
        "execution_authorized": False,
        "note": "Calibration evidence only; duplicate outcomes are excluded; eligibility is not execution authorization.",
        "stats": summaries,
    }


def write_hot_path_calibration(
    outcomes_path: str | Path,
    report_path: str | Path,
    *,
    min_samples: int = 100,
) -> dict[str, Any]:
    report = build_hot_path_calibration(outcomes_path, min_samples=min_samples)
    destination = Path(report_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2), encoding="utf-8")
    temporary.replace(destination)
    return report
