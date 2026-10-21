from __future__ import annotations

import json

from PC_ENGINE.diagnostics.operational import latest_events_by_venue_symbol


def test_unknown_websocket_latency_stays_unknown_in_diagnostics(tmp_path):
    path = tmp_path / "websocket_events.jsonl"
    path.write_text(
        "\n".join(
            [
                json.dumps({"exchange": "binance", "symbol": "BTC/USDT", "local_ts_ms": 100, "exchange_ts_ms": 90, "price": 100}),
                json.dumps({"exchange": "okx", "symbol": "BTC/USDT", "local_ts_ms": 101, "exchange_ts_ms": 91, "local_receive_latency_ms": None, "price": 100}),
                json.dumps({"exchange": "coinbase", "symbol": "BTC/USDT", "local_ts_ms": 102, "exchange_ts_ms": 92, "local_receive_latency_ms": "invalid", "price": 100}),
                json.dumps({"exchange": "kraken", "symbol": "BTC/USDT", "local_ts_ms": 103, "exchange_ts_ms": 93, "local_receive_latency_ms": 0, "price": 100}),
                json.dumps({"exchange": "bybit", "symbol": "BTC/USDT", "local_ts_ms": 104, "exchange_ts_ms": 94, "local_receive_latency_ms": 7, "price": 100}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    latest = latest_events_by_venue_symbol(path)

    assert latest["binance"]["BTC/USDT"]["latency_ms"] is None
    assert latest["okx"]["BTC/USDT"]["latency_ms"] is None
    assert latest["coinbase"]["BTC/USDT"]["latency_ms"] is None
    assert latest["kraken"]["BTC/USDT"]["latency_ms"] == 0
    assert latest["bybit"]["BTC/USDT"]["latency_ms"] == 7
