from __future__ import annotations

import json
from pathlib import Path

from PC_ENGINE.radar.lead_lag_learning import LeadLagLearningEngine


def test_learning_marks_positive_relationship(tmp_path: Path):
    radar = tmp_path
    candidates = []
    events = []
    for i in range(120):
        base = 1_000_000 + i * 10_000
        candidates.append({"symbol":"BTC/USDT","leader":"okx","follower":"binance","direction":"UP",
                           "leader_exchange_ts_ms":base,"follower_exchange_ts_ms":base+50,"exchange_lag_ms":50})
        events += [
            {"event":{"exchange":"binance","symbol":"BTC/USDT","price":100+i*0.01,"quantity":1,"side":"BUY","exchange_ts_ms":base+50,"local_ts_ms":base+55,"local_receive_latency_ms":5}},
            {"event":{"exchange":"binance","symbol":"BTC/USDT","price":100+i*0.01+0.02,"quantity":1,"side":"BUY","exchange_ts_ms":base+1050,"local_ts_ms":base+1055,"local_receive_latency_ms":5}},
        ]
    (radar / "websocket_lead_lag.jsonl").write_text("\n".join(json.dumps(x) for x in candidates))
    (radar / "websocket_events.jsonl").write_text("\n".join(json.dumps(x) for x in events))
    stats = LeadLagLearningEngine(radar, min_samples=100, fee_bps_per_side=0, slippage_bps_per_side=0).learn((1000,))
    assert stats and stats[0].samples == 120
    assert stats[0].expectancy_bps > 0
    assert stats[0].eligible is True


def test_small_sample_is_not_eligible(tmp_path: Path):
    engine = LeadLagLearningEngine(tmp_path, min_samples=100)
    stats = engine.learn()
    assert stats == []
    assert not engine.eligible_signals(stats)
