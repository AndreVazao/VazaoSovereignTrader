from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def _tail_jsonl(path: Path, max_bytes: int = 262_144) -> list[dict[str, Any]]:
    if not path.exists() or not path.is_file():
        return []
    try:
        with path.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            handle.seek(max(0, size - max_bytes))
            raw = handle.read().decode("utf-8", errors="replace")
    except OSError:
        return []
    rows: list[dict[str, Any]] = []
    for line in raw.splitlines():
        try:
            value = json.loads(line)
        except (TypeError, ValueError):
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def latest_events_by_venue_symbol(path: str | Path) -> dict[str, dict[str, dict[str, Any]]]:
    latest: dict[str, dict[str, dict[str, Any]]] = {}
    for row in _tail_jsonl(Path(path)):
        venue = str(row.get("exchange", "")).lower()
        symbol = str(row.get("symbol", "")).upper()
        if not venue or not symbol:
            continue
        current = latest.setdefault(venue, {}).get(symbol)
        ts = int(row.get("local_ts_ms") or 0)
        if current is None or ts >= int(current.get("local_ts_ms") or 0):
            latest[venue][symbol] = {
                "symbol": symbol,
                "local_ts_ms": ts,
                "exchange_ts_ms": int(row.get("exchange_ts_ms") or 0),
                "price": row.get("price"),
                "latency_ms": int(row.get("local_receive_latency_ms") or 0),
            }
    return {venue: dict(sorted(symbols.items())) for venue, symbols in sorted(latest.items())}


def storage_metrics(root: str | Path, previous_bytes: int | None = None) -> dict[str, Any]:
    base = Path(root)
    total = 0
    files = 0
    jsonl_bytes = 0
    largest: list[dict[str, Any]] = []
    if base.exists():
        for path in base.rglob("*"):
            try:
                if not path.is_file():
                    continue
                size = path.stat().st_size
            except OSError:
                continue
            total += size
            files += 1
            if path.suffix.lower() == ".jsonl":
                jsonl_bytes += size
            largest.append({"path": str(path), "bytes": size})
    largest.sort(key=lambda row: (-int(row["bytes"]), row["path"]))
    result: dict[str, Any] = {
        "root": str(base),
        "files": files,
        "bytes": total,
        "jsonl_bytes": jsonl_bytes,
        "largest_files": largest[:10],
    }
    if previous_bytes is not None:
        result["previous_bytes"] = int(previous_bytes)
        result["growth_bytes"] = total - int(previous_bytes)
    return result


def build_operational_diagnostics(*, engine: dict[str, Any], market_data: dict[str, Any],
                                  latest_events: dict[str, dict[str, dict[str, Any]]],
                                  storage: dict[str, Any], recovery: dict[str, Any] | None = None) -> dict[str, Any]:
    radar = dict(market_data.get("radar") or {})
    return {
        "schema_version": 1,
        "paper_only": str(engine.get("mode", "PAPER")).upper() == "PAPER",
        "engine": {
            "status": engine.get("status"),
            "mode": engine.get("mode"),
            "balance": engine.get("balance"),
            "equity": engine.get("equity"),
            "watchdog": engine.get("watchdog") or {},
            "preflight": engine.get("preflight") or {},
            "reconciliation": engine.get("account_reconciliation") or {},
            "financial_reconciliation": engine.get("financial_reconciliation") or {},
        },
        "market_data": {
            "status": market_data.get("status"),
            "ok": market_data.get("ok"),
            "stale": market_data.get("stale"),
            "health_age_ms": market_data.get("health_age_ms"),
            "events_total": radar.get("events_total", 0),
            "events_by_exchange": radar.get("events_by_exchange") or {},
            "last_event": radar.get("last_event") or {},
            "last_event_age_ms": radar.get("last_event_age_ms") or {},
            "reconnects": radar.get("reconnects") or {},
            "errors": radar.get("errors") or {},
            "latest_by_venue_symbol": latest_events,
        },
        "storage": storage,
        "recovery": dict(recovery or {}),
        "diagnostics": {
            "real_promotion_attempted": False,
            "orders_submitted": False,
            "cloud_required": False,
        },
    }
