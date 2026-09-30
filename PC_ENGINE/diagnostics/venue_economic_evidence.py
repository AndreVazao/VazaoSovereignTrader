from __future__ import annotations

import hashlib
import json
import math
import random
import statistics
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

from PC_ENGINE.radar.report_io import atomic_write_json


def _finite(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def _configured_venues(config: dict[str, Any]) -> list[str]:
    radar = config.get("radar", {})
    if not isinstance(radar, dict):
        radar = {}
    names: list[str] = []

    def add(values: Any) -> None:
        if not isinstance(values, (list, tuple, set)):
            return
        for value in values:
            if isinstance(value, str) and value.strip():
                name = value.strip().lower()
                if name not in names:
                    names.append(name)

    add(radar.get("polling_exchanges"))
    add(radar.get("websocket_exchanges"))
    universe = config.get("market_universe", {})
    assets = universe.get("assets", {}) if isinstance(universe, dict) else {}
    spot = assets.get("crypto_spot", {}) if isinstance(assets, dict) else {}
    if isinstance(spot, dict):
        add(spot.get("venues"))
    return names


def _load_outcomes(path: Path, *, now_ms: int, max_records: int) -> tuple[list[dict[str, Any]], dict[str, int]]:
    limit = max(1, int(max_records))
    counters = {"raw_lines_seen": 0, "malformed_lines_ignored": 0, "invalid_outcomes_ignored": 0,
                "non_paper_records_ignored": 0, "duplicate_outcomes_ignored": 0,
                "records_omitted_by_limit": 0}
    rows: deque[dict[str, Any]] = deque(maxlen=limit)
    seen: set[str] = set()
    try:
        handle = path.open("rb")
    except OSError:
        return [], counters
    with handle:
        for raw in handle:
            if not raw.strip():
                continue
            counters["raw_lines_seen"] += 1
            try:
                row = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                counters["malformed_lines_ignored"] += 1
                continue
            if not isinstance(row, dict):
                counters["invalid_outcomes_ignored"] += 1
                continue
            if row.get("status") != "COMPLETED" or row.get("paper_only") is not True or row.get("orders_submitted") is not False:
                counters["non_paper_records_ignored"] += 1
                continue
            try:
                symbol = str(row["symbol"]).strip().upper()
                follower = str(row["follower"]).strip().lower()
                leader = str(row["leader"]).strip().lower()
                ts_raw = row["outcome_local_ts_ms"]
                if isinstance(ts_raw, bool):
                    raise ValueError("boolean timestamp")
                ts = int(ts_raw)
                net = _finite(row["realized_net_bps"])
                if not symbol or not follower or not leader or ts <= 0 or ts > now_ms or net is None:
                    raise ValueError("invalid required outcome")
            except (KeyError, TypeError, ValueError, OverflowError):
                counters["invalid_outcomes_ignored"] += 1
                continue
            identity = str(row.get("outcome_id") or json.dumps(
                [symbol, leader, follower, row.get("direction"), row.get("horizon_ms"), ts],
                separators=(",", ":"), ensure_ascii=False,
            ))
            if identity in seen:
                counters["duplicate_outcomes_ignored"] += 1
                continue
            normalized = dict(row)
            normalized.update({"symbol": symbol, "leader": leader, "follower": follower,
                               "outcome_local_ts_ms": ts, "realized_net_bps": net})
            for key in ("fees_bps", "slippage_bps", "latency_penalty_bps"):
                normalized[key] = _finite(row.get(key))
            if len(rows) == rows.maxlen:
                evicted = rows.popleft()
                seen.discard(str(evicted["_economic_identity"]))
                counters["records_omitted_by_limit"] += 1
            normalized["_economic_identity"] = identity
            rows.append(normalized)
            seen.add(identity)
    ordered = sorted(rows, key=lambda row: row["outcome_local_ts_ms"])
    for row in ordered:
        row.pop("_economic_identity", None)
    return ordered, counters



def _moving_block_bootstrap_ci(values: list[float], *, seed_key: str, replicates: int = 1000) -> dict[str, Any]:
    """Deterministic mean interval preserving short-range chronological dependence."""
    n = len(values)
    if n < 8:
        return {
            "assessment": "UNAVAILABLE",
            "method": "moving_block_bootstrap",
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
    for _ in range(max(500, int(replicates))):
        sample: list[float] = []
        while len(sample) < n:
            start = rng.choice(block_starts)
            sample.extend(values[start:start + block_length])
        means.append(statistics.fmean(sample[:n]))
    means.sort()
    low_index = int(0.025 * (len(means) - 1))
    high_index = int(0.975 * (len(means) - 1))
    return {
        "assessment": "AVAILABLE",
        "method": "moving_block_bootstrap",
        "bootstrap_replicates": len(means),
        "block_length": block_length,
        "lower": means[low_index],
        "upper": means[high_index],
    }


def build_venue_economic_evidence(
    config: dict[str, Any],
    outcomes_path: str | Path,
    *,
    now_ms: int | None = None,
    min_samples: int = 30,
    min_oos_samples: int = 8,
    max_records: int = 100000,
) -> dict[str, Any]:
    """Descriptive PAPER economics per configured follower venue; never authorizes execution."""
    now = int(now_ms if now_ms is not None else time.time_ns() // 1_000_000)
    min_samples = max(1, int(min_samples))
    min_oos_samples = max(1, int(min_oos_samples))
    rows, counters = _load_outcomes(Path(outcomes_path), now_ms=now, max_records=max_records)
    configured = _configured_venues(config)
    by_follower: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_follower[row["follower"]].append(row)

    venues: list[dict[str, Any]] = []
    for venue in configured:
        sample = by_follower.get(venue, [])
        count = len(sample)
        test_count = max(1, int(math.ceil(count * 0.30))) if count else 0
        test = sample[-test_count:] if test_count else []
        net_values = [row["realized_net_bps"] for row in test]
        enough = count >= min_samples and len(test) >= min_oos_samples
        mean_oos = statistics.fmean(net_values) if net_values else None
        ci = _moving_block_bootstrap_ci(
            net_values,
            seed_key=f"{venue}:{count}:{sample[0]['outcome_local_ts_ms'] if sample else 0}:{sample[-1]['outcome_local_ts_ms'] if sample else 0}",
        )
        ci_available = ci["assessment"] == "AVAILABLE"
        status = "INSUFFICIENT_DATA"
        if enough and not ci_available:
            status = "INSUFFICIENT_OOS_FOR_CI"
        elif enough and ci_available:
            if ci["lower"] is not None and ci["lower"] > 0:
                status = "POSITIVE_OOS_CANDIDATE"
            elif ci["upper"] is not None and ci["upper"] < 0:
                status = "NON_POSITIVE_OOS"
            else:
                status = "UNCERTAIN_OOS"
        def mean_cost(key: str) -> float | None:
            values = [row[key] for row in sample if row.get(key) is not None]
            return round(statistics.fmean(values), 6) if values else None
        venues.append({
            "venue": venue,
            "role": "PAPER_FOLLOWER_EXECUTION_PROXY",
            "status": status,
            "paper_outcome_samples": count,
            "oos_samples": len(test),
            "min_samples_required": min_samples,
            "min_oos_samples_required": min_oos_samples,
            "oos_mean_realized_net_bps": round(mean_oos, 6) if mean_oos is not None else None,
            "oos_ci95_lower_bps": round(ci["lower"], 6) if ci["lower"] is not None else None,
            "oos_ci95_upper_bps": round(ci["upper"], 6) if ci["upper"] is not None else None,
            "oos_ci95_method": ci["method"],
            "oos_bootstrap_replicates": ci["bootstrap_replicates"],
            "oos_bootstrap_block_length": ci["block_length"],
            "oos_confidence_interval_available": ci_available,
            "oos_edge_supported": bool(ci_available and ci["lower"] is not None and ci["lower"] > 0),
            "oos_positive_rate": round(sum(value > 0 for value in net_values) / len(net_values), 6) if net_values else None,
            "mean_recorded_fees_bps": mean_cost("fees_bps"),
            "mean_recorded_slippage_bps": mean_cost("slippage_bps"),
            "mean_recorded_latency_penalty_bps": mean_cost("latency_penalty_bps"),
            "spread_bps": None,
            "spread_status": "UNAVAILABLE_NO_BID_ASK_EVIDENCE",
            "notes": "Net outcomes are PAPER observations under recorded cost assumptions, not fills or a profitability guarantee. A positive OOS mean is insufficient on its own; a candidate requires the deterministic moving-block bootstrap 95% interval lower bound above zero. This remains a PAPER review candidate only.",
        })

    return {
        "schema_version": 1,
        "generated_at_ms": now,
        "source": Path(outcomes_path).name,
        "configured_venues_only": True,
        "venues": venues,
        "integrity": counters,
        "paper_only": True,
        "orders_submitted": False,
        "execution_authorized": False,
        "note": "Economic evidence is separate from operational health. No venue is automatically removed or promoted; spread remains unavailable until valid bid/ask observations are collected; OOS uncertainty is reported with a deterministic moving-block bootstrap interval.",
    }


def write_venue_economic_evidence(
    config: dict[str, Any],
    outcomes_path: str | Path,
    report_path: str | Path,
    *,
    now_ms: int | None = None,
    min_samples: int = 30,
    min_oos_samples: int = 8,
    max_records: int = 100000,
) -> dict[str, Any]:
    report = build_venue_economic_evidence(
        config, outcomes_path, now_ms=now_ms, min_samples=min_samples,
        min_oos_samples=min_oos_samples, max_records=max_records,
    )
    atomic_write_json(Path(report_path), report)
    report["report_path"] = str(report_path)
    return report
