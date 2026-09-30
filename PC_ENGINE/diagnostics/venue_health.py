from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


def _configured_exchanges(config: dict[str, Any]) -> list[str]:
    radar = config.get("radar", {})
    names: list[str] = []
    for key in ("polling_exchanges", "websocket_exchanges"):
        for value in radar.get(key, []) or []:
            name = str(value).strip().lower()
            if name and name not in names:
                names.append(name)
    for value in config.get("market_universe", {}).get("assets", {}).get("crypto_spot", {}).get("venues", []) or []:
        name = str(value).strip().lower()
        if name and name not in names:
            names.append(name)
    for value in config.get("capital_venue_discovery", {}).get("venues", []) or []:
        name = str(value).strip().lower()
        if name and name not in names:
            names.append(name)
    return names


def _read_recent_jsonl(path: Path, limit: int = 4000) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as handle:
            lines = handle.readlines()[-max(1, int(limit)):]
    except OSError:
        return []
    rows: list[dict[str, Any]] = []
    for line in lines:
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def _venue_activity(data_dir: Path, exchange: str) -> dict[str, int | None]:
    observation_rows = _read_recent_jsonl(data_dir / "observations.jsonl")
    websocket_rows = _read_recent_jsonl(data_dir / "websocket_events.jsonl")
    observation_count = 0
    websocket_count = 0
    last_observation_ms: int | None = None
    last_websocket_ms: int | None = None

    for row in observation_rows:
        row_ts = int(row.get("local_ts_ms", 0) or 0)
        for snapshot in row.get("snapshots", []) or []:
            if str(snapshot.get("exchange", "")).lower() != exchange:
                continue
            observation_count += 1
            ts = int(snapshot.get("local_ts_ms", row_ts) or row_ts)
            if ts > 0:
                last_observation_ms = max(last_observation_ms or ts, ts)

    for row in websocket_rows:
        if str(row.get("exchange", "")).lower() != exchange:
            continue
        websocket_count += 1
        ts = int(row.get("local_ts_ms", 0) or 0)
        if ts > 0:
            last_websocket_ms = max(last_websocket_ms or ts, ts)

    latest = max(x for x in (last_observation_ms, last_websocket_ms) if x is not None) if any(
        x is not None for x in (last_observation_ms, last_websocket_ms)
    ) else None
    return {
        "observation_samples": observation_count,
        "websocket_events": websocket_count,
        "last_observation_ms": last_observation_ms,
        "last_websocket_ms": last_websocket_ms,
        "last_activity_ms": latest,
    }


def build_venue_health(config: dict[str, Any], *, now_ms: int | None = None) -> dict[str, Any]:
    now = int(now_ms if now_ms is not None else time.time_ns() // 1_000_000)
    radar = config.get("radar", {})
    data_dir = Path(radar.get("data_dir", "PC_ENGINE/data/radar"))
    freshness_seconds = max(5, int(radar.get("health_stale_seconds", 30)))
    green_samples = max(1, int(radar.get("venue_health_min_samples", 3)))
    red_after_seconds = max(freshness_seconds * 5, int(radar.get("venue_health_red_after_seconds", freshness_seconds * 5)))

    polling = {str(x).lower() for x in radar.get("polling_exchanges", []) or []}
    websocket = {str(x).lower() for x in radar.get("websocket_exchanges", []) or []}

    venues: list[dict[str, Any]] = []
    for exchange in _configured_exchanges(config):
        activity = _venue_activity(data_dir, exchange)
        last_activity = activity["last_activity_ms"]
        age_ms = None if last_activity is None else max(0, now - int(last_activity))
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

    counts = {status: sum(1 for venue in venues if venue["status"] == status) for status in ("GREEN", "YELLOW", "RED")}
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
        "note": "Sinalética operacional baseada em dados observados. Não é uma avaliação de rentabilidade nem autoriza execução. RED gera candidato a revisão; o descarte definitivo exige evidência adicional.",
    }
