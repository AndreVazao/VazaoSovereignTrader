from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from PC_ENGINE.diagnostics.path_utils import resolve_config_path


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _items(value: Any) -> list[Any]:
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return []


def _timestamp_ms(value: Any, *, now_ms: int) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        timestamp = int(value)
    except (TypeError, ValueError, OverflowError):
        return None
    # Future timestamps must not make a venue appear fresh/healthy.
    if timestamp <= 0 or timestamp > now_ms:
        return None
    return timestamp


def _configured_exchanges(config: dict[str, Any]) -> list[str]:
    root = _mapping(config)
    radar = _mapping(root.get("radar"))
    names: list[str] = []

    def add_values(values: Any) -> None:
        for value in _items(values):
            if not isinstance(value, str):
                continue
            name = str(value).strip().lower()
            if name and name not in names:
                names.append(name)

    for key in ("polling_exchanges", "websocket_exchanges"):
        add_values(radar.get(key))

    market_universe = _mapping(root.get("market_universe"))
    assets = _mapping(market_universe.get("assets"))
    crypto_spot = _mapping(assets.get("crypto_spot"))
    add_values(crypto_spot.get("venues"))
    add_values(_mapping(root.get("capital_venue_discovery")).get("venues"))
    return names


def _read_recent_jsonl(path: Path, limit: int = 4000) -> list[dict[str, Any]]:
    try:
        with path.open("rb") as handle:
            lines = handle.readlines()[-max(1, int(limit)):]
    except (OSError, TypeError, ValueError, OverflowError):
        return []

    rows: list[dict[str, Any]] = []
    for raw_line in lines:
        try:
            line = raw_line.decode("utf-8")
            value = json.loads(line)
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def _venue_activity(
    data_dir: Path, exchange: str, *, now_ms: int
) -> dict[str, int | None]:
    observation_rows = _read_recent_jsonl(data_dir / "observations.jsonl")
    websocket_rows = _read_recent_jsonl(data_dir / "websocket_events.jsonl")
    observation_count = 0
    websocket_count = 0
    last_observation_ms: int | None = None
    last_websocket_ms: int | None = None

    for row in observation_rows:
        row_ts = _timestamp_ms(row.get("local_ts_ms"), now_ms=now_ms)
        snapshots = row.get("snapshots", [])
        for snapshot in _items(snapshots):
            if not isinstance(snapshot, dict):
                continue
            if str(snapshot.get("exchange", "")).strip().lower() != exchange:
                continue
            ts = _timestamp_ms(snapshot.get("local_ts_ms"), now_ms=now_ms) or row_ts
            if ts is not None:
                observation_count += 1
                last_observation_ms = max(last_observation_ms or ts, ts)

    for row in websocket_rows:
        if str(row.get("exchange", "")).strip().lower() != exchange:
            continue
        ts = _timestamp_ms(row.get("local_ts_ms"), now_ms=now_ms)
        if ts is not None:
            websocket_count += 1
            last_websocket_ms = max(last_websocket_ms or ts, ts)

    timestamps = [
        timestamp for timestamp in (last_observation_ms, last_websocket_ms)
        if timestamp is not None
    ]
    latest = max(timestamps) if timestamps else None
    return {
        "observation_samples": observation_count,
        "websocket_events": websocket_count,
        "last_observation_ms": last_observation_ms,
        "last_websocket_ms": last_websocket_ms,
        "last_activity_ms": latest,
    }


def build_venue_health(config: dict[str, Any], *, now_ms: int | None = None) -> dict[str, Any]:
    now = int(now_ms if now_ms is not None else time.time_ns() // 1_000_000)
    root = _mapping(config)
    radar = _mapping(root.get("radar"))
    try:
        data_dir = resolve_config_path(radar.get("data_dir", "PC_ENGINE/data/radar"))
    except (TypeError, ValueError):
        data_dir = resolve_config_path("PC_ENGINE/data/radar")

    def positive_int(key: str, default: int, minimum: int) -> int:
        try:
            return max(minimum, int(radar.get(key, default)))
        except (TypeError, ValueError, OverflowError):
            return max(minimum, default)

    freshness_seconds = positive_int("health_stale_seconds", 30, 5)
    green_samples = positive_int("venue_health_min_samples", 3, 1)
    red_after_seconds = max(
        freshness_seconds * 5,
        positive_int("venue_health_red_after_seconds", freshness_seconds * 5, freshness_seconds * 5),
    )

    polling = {
        str(x).strip().lower()
        for x in _items(radar.get("polling_exchanges"))
        if isinstance(x, str) and str(x).strip()
    }
    websocket = {
        str(x).strip().lower()
        for x in _items(radar.get("websocket_exchanges"))
        if isinstance(x, (str, int, float)) and str(x).strip()
    }

    venues: list[dict[str, Any]] = []
    for exchange in _configured_exchanges(root):
        activity = _venue_activity(data_dir, exchange, now_ms=now)
        last_activity = activity["last_activity_ms"]
        age_ms = None if last_activity is None else now - int(last_activity)
        sample_count = int(activity["observation_samples"]) + int(activity["websocket_events"])
        role = []
        if exchange in polling:
            role.append("POLLING")
        if exchange in websocket:
            role.append("WEBSOCKET")
        if not role:
            role.append("RESEARCH")

        if last_activity is None:
            status = "RED"
            label = "SEM DADOS"
            hint = "REVIEW / CANDIDATO A DESCARTE"
            detail = "Configurada, mas sem observações válidas registadas."
        elif age_ms is not None and age_ms <= freshness_seconds * 1000 and sample_count >= green_samples:
            status = "GREEN"
            label = "OK"
            hint = "MANTER"
            detail = "Dados recentes e volume mínimo de observações atingido."
        elif age_ms is not None and age_ms <= red_after_seconds * 1000:
            status = "YELLOW"
            label = "EM TESTE"
            hint = "OBSERVAR"
            detail = "Há dados, mas a recência ou a amostra ainda não suporta classificação operacional forte."
        else:
            status = "RED"
            label = "INDISPONÍVEL"
            hint = "REVIEW / CANDIDATO A DESCARTE"
            detail = "Sem dados recentes dentro da janela operacional definida."

        venues.append({
            "exchange": exchange,
            "status": status,
            "label": label,
            "decision_hint": hint,
            "detail": detail,
            "role": role,
            "sample_count": sample_count,
            "observation_samples": int(activity["observation_samples"]),
            "websocket_events": int(activity["websocket_events"]),
            "last_activity_ms": last_activity,
            "age_ms": age_ms,
            "freshness_window_seconds": freshness_seconds,
            "paper_only": True,
            "orders_submitted": False,
        })

    counts = {
        status: sum(1 for venue in venues if venue["status"] == status)
        for status in ("GREEN", "YELLOW", "RED")
    }
    return {
        "generated_at_ms": now,
        "venues": venues,
        "counts": counts,
        "status_legend": {
            "GREEN": "operacionalmente saudável segundo recência/amostra",
            "YELLOW": "em teste ou com evidência insuficiente",
            "RED": "sem dados válidos ou indisponível; candidato a revisão, não descarte automático",
        },
        "paper_only": True,
        "orders_submitted": False,
        "execution_authorized": False,
        "note": "Sinalética operacional baseada em dados observados. Não é uma avaliação de rentabilidade nem autoriza execução. RED gera candidato a revisão; não existe descarte automático e o descarte definitivo exige evidência adicional.",
    }
