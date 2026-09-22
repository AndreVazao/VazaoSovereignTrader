from __future__ import annotations
import json
from pathlib import Path
from PC_ENGINE.radar.lead_lag_validation import LeadLagValidationEngine

def test_validation_separates_time_windows(tmp_path: Path):
    candidates=[]; events=[]
    for i in range(20):
        base=1000+i*2000
        candidates.append({"symbol":"BTC/USDT","leader":"binance","follower":"okx","direction":"UP","leader_exchange_ts_ms":base,"follower_exchange_ts_ms":base+100,"exchange_lag_ms":100})
        events.extend([
            {"exchange":"okx","symbol":"BTC/USDT","exchange_ts_ms":base+100,"price":100.0},
            {"exchange":"okx","symbol":"BTC/USDT","exchange_ts_ms":base+1100,"price":100.5},
        ])
    (tmp_path/"websocket_lead_lag.jsonl").write_text("".join(json.dumps(x)+"\n" for x in candidates),encoding="utf-8")
    (tmp_path/"websocket_events.jsonl").write_text("".join(json.dumps(x)+"\n" for x in events),encoding="utf-8")
    rows=LeadLagValidationEngine(tmp_path,split_ratio=.7,min_in_samples=5,min_out_samples=5,cost_bps=1).validate(1000)
    assert rows and rows[0].in_samples>=5 and rows[0].out_samples>=5 and rows[0].stable is True
