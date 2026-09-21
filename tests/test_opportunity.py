from PC_ENGINE.core.opportunity import PaperOpportunityEngine


def test_opportunity_without_learning_uses_strategy_and_cost():
    engine = PaperOpportunityEngine({"learning_weight": 0.25, "cost_weight": 0.15})
    result = engine.score(
        symbol="BTC/USDT",
        strategy_score=0.8,
        action="BUY",
        spread_pct=0.0005,
        state=None,
        now_ms=1_000,
    )
    assert 0.0 < result.score < 0.8
    assert result.learning_bonus == 0.0


def test_non_buy_never_becomes_opportunity():
    engine = PaperOpportunityEngine()
    result = engine.score(
        symbol="ETH/USDT",
        strategy_score=0.9,
        action="SELL",
        spread_pct=0.0,
        state=None,
        now_ms=1_000,
    )
    assert result.score == 0.0
    assert result.confidence == 0.0


def test_fresh_eligible_latency_edge_adds_bounded_paper_bonus(tmp_path):
    import json

    path = tmp_path / "latency.jsonl"
    path.write_text(json.dumps({
        "symbol": "BTC/USDT",
        "direction": "UP",
        "eligible": True,
        "observed_ts_ms": 9900,
        "net_expected_edge_bps": 3.0,
        "same_direction_ratio": 0.9,
        "persistence_ratio": 0.8,
    }) + "\n", encoding="utf-8")
    engine = PaperOpportunityEngine({
        "latency_path": str(path),
        "latency_weight": 0.15,
        "latency_max_bonus": 0.15,
        "latency_stale_after_ms": 1000,
        "latency_min_edge_bps": 1.0,
    })
    result = engine.score(
        symbol="BTC/USDT",
        strategy_score=0.6,
        action="BUY",
        spread_pct=0.0,
        state=None,
        now_ms=10_000,
    )
    assert result.latency_edge_bps == 3.0
    assert result.latency_freshness == 0.9
    assert 0.0 < result.latency_bonus <= 0.15
    assert result.score > 0.6


def test_stale_latency_edge_does_not_affect_paper_opportunity(tmp_path):
    import json

    path = tmp_path / "latency.jsonl"
    path.write_text(json.dumps({
        "symbol": "ETH/USDT",
        "direction": "UP",
        "eligible": True,
        "observed_ts_ms": 1_000,
        "net_expected_edge_bps": 5.0,
        "same_direction_ratio": 1.0,
        "persistence_ratio": 1.0,
    }) + "\n", encoding="utf-8")
    engine = PaperOpportunityEngine({
        "latency_path": str(path),
        "latency_stale_after_ms": 500,
    })
    result = engine.score(
        symbol="ETH/USDT",
        strategy_score=0.6,
        action="BUY",
        spread_pct=0.0,
        state=None,
        now_ms=2_000,
    )
    assert result.latency_bonus == 0.0
    assert result.latency_edge_bps == 0.0
