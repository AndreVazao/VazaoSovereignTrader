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


def test_venue_health_ignores_malformed_nested_rows_and_invalid_timestamps(tmp_path):
    now = 1_000_000
    (tmp_path / "observations.jsonl").write_bytes(
        b'not json\\n'
        + b'{"local_ts_ms":"not-a-time","snapshots":{"exchange":"binance"}}\\n'
        + b'{"local_ts_ms":1000001,"snapshots":[{"exchange":"binance","local_ts_ms":1000001}]}\\n'
        + b'{"local_ts_ms":999000,"snapshots":[null,42,{"exchange":"binance","local_ts_ms":"bad"}]}\\n'
        + b'{"local_ts_ms":999500,"snapshots":[{"exchange":"binance","local_ts_ms":999500}]}\\n'
        + b'\\xff\\xfe\\n'
    )
    (tmp_path / "websocket_events.jsonl").write_text(
        '{"exchange":"binance","local_ts_ms":NaN}\\n'
        '{"exchange":"binance","local_ts_ms":999800}\\n',
        encoding="utf-8",
    )

    report = build_venue_health(
        {"radar": {"data_dir": str(tmp_path), "polling_exchanges": ["binance"], "venue_health_min_samples": 2}},
        now_ms=now,
    )

    venue = report["venues"][0]
    assert venue["exchange"] == "binance"
    assert venue["status"] == "GREEN"
    assert venue["last_activity_ms"] == 999800
    assert venue["age_ms"] == 200
    assert report["execution_authorized"] is False


def test_venue_health_handles_malformed_nested_configuration(tmp_path):
    report = build_venue_health(
        {
            "radar": {
                "data_dir": str(tmp_path),
                "polling_exchanges": "binance",
                "websocket_exchanges": None,
                "health_stale_seconds": "invalid",
                "venue_health_min_samples": None,
            },
            "market_universe": {"assets": ["unexpected"]},
            "capital_venue_discovery": ["unexpected"],
        },
        now_ms=1_000_000,
    )

    assert report["venues"] == []
    assert report["counts"] == {"GREEN": 0, "YELLOW": 0, "RED": 0}
    assert report["execution_authorized"] is False
