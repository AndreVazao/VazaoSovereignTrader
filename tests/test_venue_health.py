from __future__ import annotations

import json
from pathlib import Path

from PC_ENGINE.diagnostics.venue_health import build_venue_health


def _write(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_venue_health_classifies_recent_stale_and_missing(tmp_path):
    now = 1_000_000
    data_dir = tmp_path / "radar"
    data_dir.mkdir()

    _write(
        data_dir / "observations.jsonl",
        [
            {
                "local_ts_ms": now - 1_000,
                "snapshots": [
                    {"exchange": "binance", "local_ts_ms": now - 1_000},
                    {"exchange": "coinbase", "local_ts_ms": now - 120_000},
                ],
            },
            {
                "local_ts_ms": now - 2_000,
                "snapshots": [
                    {"exchange": "binance", "local_ts_ms": now - 2_000},
                ],
            },
            {
                "local_ts_ms": now - 3_000,
                "snapshots": [
                    {"exchange": "binance", "local_ts_ms": now - 3_000},
                ],
            },
        ],
    )

    report = build_venue_health(
        {
            "radar": {
                "data_dir": str(data_dir),
                "health_stale_seconds": 30,
                "polling_exchanges": ["binance", "coinbase", "okx"],
                "websocket_exchanges": ["binance", "coinbase"],
            }
        },
        now_ms=now,
    )

    by_name = {row["exchange"]: row for row in report["venues"]}
    assert by_name["binance"]["status"] == "GREEN"
    assert by_name["coinbase"]["status"] == "YELLOW"
    assert by_name["okx"]["status"] == "RED"
    assert by_name["okx"]["decision_hint"].startswith("REVIEW")
    assert report["paper_only"] is True
    assert report["orders_submitted"] is False
    assert report["execution_authorized"] is False


def test_venue_health_does_not_call_red_an_automatic_discard(tmp_path):
    report = build_venue_health(
        {"radar": {"data_dir": str(tmp_path), "polling_exchanges": ["kraken"]}},
        now_ms=1_000_000,
    )
    venue = report["venues"][0]
    assert venue["status"] == "RED"
    assert "DESCARTE AUTOMÁTICO" not in venue["decision_hint"]
    assert "descarte automático" in report["note"]
