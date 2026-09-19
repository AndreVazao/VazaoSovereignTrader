from __future__ import annotations

import json
from pathlib import Path

from PC_ENGINE.radar.lead_lag_learning import LeadLagLearningEngine


def _event(exchange: str, symbol: str, ts: int, price: float) -> dict:
    return {
        "exchange": exchange,
        "symbol": symbol,
        "price": price,
        "quantity": 1.0,
        "side": "BUY",
        "exchange_ts_ms": ts,
        "local_ts_ms": ts,
        "local_receive_latency_ms": 1,
        "price_before": None,
    }


def test_learning_reads_collector_artifacts(tmp_path: Path) -> None:
    data = tmp_path
    events = [
        _event("binance", "BTC/USDT", 1000, 100.0),
        _event("binance", "BTC/USDT", 1100, 100.6),
        _event("okx", "BTC/USDT", 1200, 100.0),
        _event("okx", "BTC/USDT", 1300, 100.5),
        _event("okx", "BTC/USDT", 2200, 101.0),
    ]
    (data / "websocket_events.jsonl").write_text(
        "".join(json.dumps(x) + "\n" for x in events), encoding="utf-8"
    )
    candidate = {
        "symbol": "BTC/USDT",
        "leader": "binance",
        "follower": "okx",
        "direction": "UP",
        "leader_exchange_ts_ms": 1100,
        "follower_exchange_ts_ms": 1200,
        "exchange_lag_ms": 100,
        "leader_receive_ts_ms": 1100,
        "follower_receive_ts_ms": 1200,
        "receive_lag_ms": 100,
        "leader_move_bps": 60.0,
        "follower_move_bps": 50.0,
    }
    (data / "websocket_lead_lag.jsonl").write_text(json.dumps(candidate) + "\n", encoding="utf-8")

    stats = LeadLagLearningEngine(data, min_samples=1, fee_bps_per_side=1, slippage_bps_per_side=1).learn([1000])
    assert stats
    assert stats[0].leader == "binance"
    assert stats[0].follower == "okx"
    assert stats[0].samples == 1
    assert stats[0].eligible is True
