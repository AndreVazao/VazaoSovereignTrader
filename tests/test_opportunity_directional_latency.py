from __future__ import annotations

import json

from PC_ENGINE.core.opportunity import PaperOpportunityEngine


def test_opportunity_uses_direction_specific_external_latency_profile(tmp_path):
    path = tmp_path / "profiles.jsonl"
    now_ms = 1_000_000
    rows = [
        {
            "symbol": "BTC/USDT",
            "direction": "UP",
            "eligible": True,
            "observed_ts_ms": now_ms - 10,
            "net_edge_bps": 4.0,
            "same_direction_ratio": 0.9,
        },
        {
            "symbol": "BTC/USDT",
            "direction": "DOWN",
            "eligible": True,
            "observed_ts_ms": now_ms - 10,
            "net_edge_bps": 7.0,
            "same_direction_ratio": 0.95,
        },
    ]
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

    engine = PaperOpportunityEngine(
        {
            "external_latency_profile_path": str(path),
            "external_latency_stale_after_ms": 2_000,
            "external_latency_weight": 0.10,
        }
    )

    sell = engine.score(
        symbol="BTC/USDT",
        strategy_score=0.8,
        action="SELL",
        spread_pct=0.0,
        state=None,
        now_ms=now_ms,
    )

    assert sell.action == "SELL"
    assert sell.external_latency_edge_bps == 7.0
    assert sell.external_latency_bonus > 0.0


def test_unknown_opportunity_action_remains_non_actionable():
    engine = PaperOpportunityEngine()
    result = engine.score(
        symbol="BTC/USDT",
        strategy_score=0.8,
        action="HOLD",
        spread_pct=0.0,
        state=None,
        now_ms=1_000_000,
    )
    assert result.score == 0.0
    assert result.action == "HOLD"
