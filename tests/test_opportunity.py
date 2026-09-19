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
