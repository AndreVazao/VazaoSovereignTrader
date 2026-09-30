from __future__ import annotations

import json
from pathlib import Path
from statistics import mean, median


def _read_jsonl(path: str | Path, limit: int = 200_000) -> list[dict]:
    target = Path(path)
    if not target.exists():
        return []
    rows = []
    with target.open("rb") as handle:
        for raw in handle.readlines()[-max(1, int(limit)):]:
            try:
                value = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            if isinstance(value, dict):
                rows.append(value)
    return rows


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = (len(ordered) - 1) * p
    lo = int(index)
    hi = min(lo + 1, len(ordered) - 1)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (index - lo)


def validate_websocket_timing(
    events: list[dict],
    lead_lag: list[dict] | None = None,
    *,
    max_receive_latency_ms: int = 2000,
    max_lead_ms: int = 750,
    min_samples: int = 100,
) -> dict:
    latencies = []
    negative_latency = 0
    invalid_timestamps = 0
    duplicates = 0
    out_of_order = 0
    last_by_venue_symbol: dict[tuple[str, str], int] = {}
    seen = set()

    for row in events:
        try:
            venue = str(row["exchange"]).lower()
            symbol = str(row["symbol"]).upper()
            exchange_ts = int(row["exchange_ts_ms"])
            local_ts = int(row["local_ts_ms"])
            latency = int(row["local_receive_latency_ms"])
        except (KeyError, TypeError, ValueError):
            invalid_timestamps += 1
            continue
        if exchange_ts <= 0 or local_ts <= 0:
            invalid_timestamps += 1
            continue
        if latency < 0 or local_ts < exchange_ts:
            negative_latency += 1
        latencies.append(latency)
        key = (venue, symbol, exchange_ts, row.get("price"), row.get("quantity"))
        if key in seen:
            duplicates += 1
        seen.add(key)
        sequence_key = (venue, symbol)
        previous = last_by_venue_symbol.get(sequence_key)
        if previous is not None and exchange_ts < previous:
            out_of_order += 1
        last_by_venue_symbol[sequence_key] = max(exchange_ts, previous or exchange_ts)

    lag_rows = lead_lag or []
    valid_lags = []
    lag_mismatches = 0
    for row in lag_rows:
        try:
            exchange_lag = int(row["exchange_lag_ms"])
            receive_lag = int(row["receive_lag_ms"])
        except (KeyError, TypeError, ValueError):
            continue
        if exchange_lag < 0 or exchange_lag > max_lead_ms or receive_lag < 0 or receive_lag > max_lead_ms:
            lag_mismatches += 1
            continue
        valid_lags.append((exchange_lag, receive_lag))

    sample_count = len(latencies)
    p50 = median(latencies) if latencies else 0.0
    p95 = _percentile(latencies, 0.95)
    p99 = _percentile(latencies, 0.99)
    excessive = sum(1 for value in latencies if value > max_receive_latency_ms)
    lag_delta = [abs(exchange - receive) for exchange, receive in valid_lags]

    timestamp_quality = (
        sample_count >= min_samples
        and invalid_timestamps == 0
        and negative_latency == 0
        and excessive == 0
        and duplicates == 0
    )
    lead_lag_quality = (
        len(valid_lags) >= min_samples
        and lag_mismatches == 0
        and (not lag_delta or _percentile(lag_delta, 0.95) <= max_lead_ms)
    )
    return {
        "schema_version": 1,
        "paper_only": True,
        "eligible_for_economic_interpretation": bool(timestamp_quality and lead_lag_quality),
        "events": {
            "samples": sample_count,
            "invalid_timestamps": invalid_timestamps,
            "negative_latency": negative_latency,
            "duplicates": duplicates,
            "out_of_order": out_of_order,
            "excessive_latency": excessive,
            "latency_ms": {
                "mean": mean(latencies) if latencies else 0.0,
                "p50": p50,
                "p95": p95,
                "p99": p99,
                "max": max(latencies) if latencies else 0.0,
            },
        },
        "lead_lag": {
            "samples": len(valid_lags),
            "rejected_timestamp_pairs": lag_mismatches,
            "exchange_vs_receive_lag_delta_ms": {
                "p95": _percentile(lag_delta, 0.95),
                "max": max(lag_delta) if lag_delta else 0.0,
            },
        },
        "thresholds": {
            "max_receive_latency_ms": int(max_receive_latency_ms),
            "max_lead_ms": int(max_lead_ms),
            "min_samples": int(min_samples),
        },
        "gates": {
            "timestamp_quality": timestamp_quality,
            "lead_lag_quality": lead_lag_quality,
        },
        "interpretation": (
            "Observed timing is internally consistent enough for further PAPER study."
            if timestamp_quality and lead_lag_quality
            else "Timing quality is insufficient; do not treat lead/lag observations as economically meaningful yet."
        ),
    }


def validate_paths(data_dir: str | Path, **kwargs) -> dict:
    base = Path(data_dir)
    return validate_websocket_timing(
        _read_jsonl(base / "websocket_events.jsonl"),
        _read_jsonl(base / "websocket_lead_lag.jsonl"),
        **kwargs,
    )


def write_report(report: dict, path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
