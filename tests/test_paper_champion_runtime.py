from __future__ import annotations

import json

from PC_ENGINE.radar.champion_challenger import CandidateSpec
from PC_ENGINE.radar.paper_champion_runtime import PaperChampionRuntime


def _candidate(cid: str, strategy: str, horizon: int = 1000) -> CandidateSpec:
    return CandidateSpec(
        candidate_id=cid,
        version="1.0",
        strategy=strategy,
        evidence_type="strategy",
        evidence_name=strategy,
        symbol="BTC/USDT",
        regime="TREND",
        horizon_ms=horizon,
    )


def test_shadow_runtime_delivers_identical_state_and_cost_context(tmp_path):
    runtime = PaperChampionRuntime(
        [_candidate("champion", "momentum"), _candidate("challenger", "breakout")],
        path=tmp_path / "states.jsonl",
    )
    state = {
        "symbol": "BTC/USDT", "timestamp_ms": 1000, "price": 100.0, "regime": "TREND",
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
    assert all(row["timestamp_ms"] == 1000 for row in rows)
    assert all(row["cost_context"] == cost for row in rows)
    assert all(row["shared_risk_authorized"] is True for row in rows)
    assert all(row["paper_only"] is True for row in rows)


def test_shadow_runtime_attributes_net_outcomes_after_shared_costs(tmp_path):
    runtime = PaperChampionRuntime(
        [_candidate("champion", "momentum"), _candidate("challenger", "breakout")],
        path=tmp_path / "states.jsonl",
        outcome_path=tmp_path / "outcomes.jsonl",
    )
    runtime.observe(
        {
            "symbol": "BTC/USDT", "timestamp_ms": 1000, "price": 100.0,
            "strategy_evidence": {
                "momentum": {"action": "BUY", "score": 1.0, "confidence": 1.0},
                "breakout": {"action": "SELL", "score": -1.0, "confidence": 1.0},
            },
        },
        cost_context={"fee_bps": 5.0, "spread_bps": 1.0},
        shared_risk_authorized=True,
    )
    assert runtime.observe(
        {"symbol": "BTC/USDT", "timestamp_ms": 2000, "price": 101.0}
    ) == 2
    rows = [json.loads(line) for line in (tmp_path / "outcomes.jsonl").read_text().splitlines()]
    assert len(rows) == 2
    by_id = {row["candidate_id"]: row for row in rows}
    assert round(by_id["champion"]["net_bps"], 6) == 94.0
    assert round(by_id["challenger"]["net_bps"], 6) == -106.0
    assert all(row["cost_bps"] == 6.0 for row in rows)
    assert all(row["paper_only"] is True for row in rows)


def test_invalid_cost_context_fails_closed(tmp_path):
    runtime = PaperChampionRuntime([_candidate("c", "momentum")], path=tmp_path / "s.jsonl")
    state = {"symbol": "BTC/USDT", "timestamp_ms": 1000, "price": 100.0}
    try:
        runtime.observe(state, cost_context={"fee_bps": float("nan")})
    except ValueError:
        pass
    else:
        raise AssertionError("invalid cost context must fail closed")
