from __future__ import annotations

import json

from PC_ENGINE.radar.champion_challenger import CandidateSpec
from PC_ENGINE.radar.paper_champion_runtime import PaperChampionRuntime


def _candidate(cid: str, strategy: str) -> CandidateSpec:
    return CandidateSpec(
        candidate_id=cid,
        version="1.0",
        strategy=strategy,
        evidence_type="strategy",
        evidence_name=strategy,
        symbol="BTC/USDT",
        regime="TREND",
        horizon_ms=1000,
    )


def test_shadow_runtime_delivers_identical_state_and_cost_context(tmp_path):
    runtime = PaperChampionRuntime(
        [_candidate("champion", "momentum"), _candidate("challenger", "breakout")],
        path=tmp_path / "states.jsonl",
    )
    state = {
        "symbol": "BTC/USDT",
        "timestamp_ms": 1000,
        "price": 100.0,
        "regime": "TREND",
        "action": "BUY",
        "strategy_evidence": {
            "momentum": {"action": "BUY", "score": 0.8, "confidence": 0.9},
            "breakout": {"action": "SELL", "score": -0.4, "confidence": 0.7},
        },
    }
    cost = {"fee_bps": 10.0, "spread_bps": 2.0}
    assert runtime.observe(state, cost_context=cost, shared_risk_authorized=True) == 2

    rows = [json.loads(line) for line in (tmp_path / "states.jsonl").read_text().splitlines()]
    assert len(rows) == 2
    assert {row["candidate_id"] for row in rows} == {"champion", "challenger"}
    assert {row["timestamp_ms"] for row in rows} == {1000}
    assert {row["price"] for row in rows} == {100.0}
    assert all(row["cost_context"] == cost for row in rows)
    assert all(row["shared_risk_authorized"] is True for row in rows)
    assert all(row["paper_only"] is True for row in rows)


def test_shadow_runtime_is_observational_only(tmp_path):
    runtime = PaperChampionRuntime(
        [_candidate("challenger", "momentum")],
        path=tmp_path / "states.jsonl",
    )
    state = {
        "symbol": "BTC/USDT",
        "timestamp_ms": 2000,
        "price": 101.0,
        "regime": "RANGE",
        "action": "HOLD",
        "strategy_evidence": {"momentum": {"action": "BUY", "score": 0.2, "confidence": 0.3}},
    }
    runtime.observe(state)
    snapshot = runtime.snapshot()
    assert snapshot["paper_only"] is True
    assert snapshot["candidate_count"] == 1
    assert snapshot["records"] == 1
