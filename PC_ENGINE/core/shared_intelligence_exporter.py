from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PC_ENGINE.core.shared_intelligence import SharedIntelligenceArtifact, SharedIntelligenceStore


def _number(payload: dict[str, Any], *keys: str, default: float = 0.0) -> float:
    for key in keys:
        if key in payload:
            try:
                return float(payload[key])
            except (TypeError, ValueError):
                return default
    return default


def _integer(payload: dict[str, Any], *keys: str, default: int = 0) -> int:
    return int(_number(payload, *keys, default=default))


def _bool(payload: dict[str, Any], *keys: str, default: bool = False) -> bool:
    for key in keys:
        if key in payload:
            return bool(payload[key])
    return default


def _strategy_visibility(payload: dict[str, Any]) -> str:
    return str(
        payload.get("strategy_visibility")
        or payload.get("visibility")
        or "SHARED"
    ).upper()


def export_learning_file(
    source_path: str | Path,
    store: SharedIntelligenceStore,
    *,
    artifact_type: str,
    producer_version: str = "1",
) -> int:
    """Export only privacy-safe, explicitly shared learning rows.

    This is an advisory-data bridge. It never exports balances, orders, P&L,
    credentials or execution authorization, and PRIVATE strategies are skipped.
    """
    source = Path(source_path)
    if not source.exists():
        return 0

    exported = 0
    with source.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            payload = row.get("artifact", row)
            if not isinstance(payload, dict):
                continue
            if _strategy_visibility(payload) != "SHARED":
                continue

            strategy_id = str(
                payload.get("strategy_id")
                or payload.get("strategy")
                or "unknown"
            ).strip()
            if not strategy_id or strategy_id == "unknown":
                continue

            sample_count = _integer(payload, "sample_count", "samples")
            win_count = _integer(payload, "win_count", "wins")
            if sample_count <= 0 or win_count < 0 or win_count > sample_count:
                continue

            artifact = SharedIntelligenceArtifact(
                artifact_type=artifact_type,
                strategy_id=strategy_id,
                market=str(payload.get("market") or payload.get("symbol") or "UNKNOWN"),
                regime=str(payload.get("regime") or "UNKNOWN"),
                horizon_seconds=max(
                    1,
                    _integer(payload, "horizon_seconds", "horizon_ms", default=1000)
                    if "horizon_seconds" in payload
                    else _integer(payload, "horizon_ms", default=1000) // 1000,
                ),
                sample_count=sample_count,
                win_count=win_count,
                win_rate=_number(payload, "win_rate", "success_rate", default=win_count / sample_count),
                mean_net_bps=_number(payload, "mean_net_bps", "mean_bps"),
                median_net_bps=_number(payload, "median_net_bps", "median_bps"),
                eligible=_bool(payload, "eligible", default=False),
                created_at_ms=_integer(payload, "created_at_ms", "timestamp_ms", "observed_ts_ms"),
                producer_version=producer_version,
            )
            store.append(artifact)
            exported += 1

    return exported
