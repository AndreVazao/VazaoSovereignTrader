from __future__ import annotations

import json

from PC_ENGINE.radar.l2_oos_validation import L2OutOfSampleValidator


def test_l2_oos_temporal_split(tmp_path):
    trades = []
    for i in range(20):
        trades.append({
            "signal_time_ms": i * 1000,
            "leader": "leader",
            "follower": "follower",
            "symbol": "BTC/USDT",
            "direction": "UP",
            "status": "COMPLETED",
            "entry_filled_qty": 1.0,
            "exit_filled_qty": 1.0,
            "net_pnl": 1.0,
            "entry_impact_bps": 2.0,
            "exit_impact_bps": 2.0,
        })
    source = tmp_path / "replay.json"
    output = tmp_path / "validation.json"
    source.write_text(json.dumps({"trades": trades}), encoding="utf-8")
    rows = L2OutOfSampleValidator(
        replay_path=str(source), output_path=str(output),
        min_in_samples=5, min_out_samples=5, min_completion_rate=0.5,
    ).validate()
    assert rows and rows[0].stable is True
    assert output.exists()


def test_l2_oos_counts_missed_signals_in_completion_and_expectancy(tmp_path):
    trades = []
    for i in range(20):
        trades.append({
            "signal_time_ms": i * 1000,
            "leader": "leader",
            "follower": "follower",
            "symbol": "BTC/USDT",
            "direction": "UP",
            "status": "COMPLETED" if i != 15 else "MISSED_ENTRY",
            "entry_filled_qty": 1.0 if i != 15 else 0.0,
            "exit_filled_qty": 1.0 if i != 15 else 0.0,
            "net_pnl": 1.0 if i != 15 else 999.0,
            "entry_impact_bps": 2.0 if i != 15 else None,
            "exit_impact_bps": 2.0 if i != 15 else None,
        })
    source = tmp_path / "replay.json"
    output = tmp_path / "validation.json"
    source.write_text(json.dumps({"trades": trades}), encoding="utf-8")
    rows = L2OutOfSampleValidator(
        replay_path=str(source), output_path=str(output),
        min_in_samples=5, min_out_samples=5, min_completion_rate=0.5,
    ).validate()
    assert rows
    assert rows[0].out_completion_rate < 1.0
