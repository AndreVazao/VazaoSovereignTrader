from __future__ import annotations

import json

from PC_ENGINE.replay.temporal import ReplayConfig, TemporalWebSocketReplay


def _event(venue: str, ts: int, price: float) -> dict:
    return {
        "event_id": f"{venue}-{ts}",
        "venue": venue,
        "symbol": "BTC/USDT",
        "event_type": "ticker",
        "sequence": ts,
        "provider_ts_ms": ts,
        "exchange_ts_ms": ts,
        "local_receive_ns": ts * 1_000_000,
        "local_receive_wall_ns": ts * 1_000_000,
        "local_process_ns": ts * 1_000_000,
        "browser_render_ns": None,
        "price": price,
        "bid": price - 0.01,
        "ask": price + 0.01,
        "volume": 1.0,
        "raw_source": "test",
    }


def test_replay_loads_and_persists(tmp_path):
    source = tmp_path / "events.jsonl"
    source.write_text(
        "\n".join([
            json.dumps(_event("binance", 1000, 100.0)),
            json.dumps(_event("okx", 1000, 100.0)),
            json.dumps(_event("binance", 1100, 100.6)),
            json.dumps(_event("okx", 1200, 100.6)),
            json.dumps(_event("okx", 2200, 101.6)),
        ]),
        encoding="utf-8",
    )
    output = tmp_path / "report.json"
    report = TemporalWebSocketReplay(ReplayConfig(
        input_path=str(source),
        output_path=str(output),
        min_move_bps=5.0,
        baseline_enabled=False,
        holding_ms=500.0,
    )).run()
    assert report.events_loaded == 5
    assert report.events_replayed == 5
    assert report.signals >= 1
    assert output.exists()
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["report"]["status"] == "PAPER_REPLAY"


def test_missing_input_is_empty(tmp_path):
    report = TemporalWebSocketReplay(ReplayConfig(
        input_path=str(tmp_path / "missing.jsonl"),
        output_path=str(tmp_path / "report.json"),
    )).run()
    assert report.status == "EMPTY"
    assert report.events_loaded == 0
