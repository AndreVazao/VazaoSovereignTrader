from PC_ENGINE.core.adaptive_risk import AdaptiveRiskController
from PC_ENGINE.core.risk import RiskEngine


def test_context_key_is_specific():
    c = AdaptiveRiskController({})
    assert c.context_key(strategy_id="latency", symbol="BTC/USDT", regime="trend", horizon_seconds=15) == "latency|BTC/USDT|trend|15"


def test_contextual_evidence_is_required_for_scaling():
    c = AdaptiveRiskController({"min_samples": 100, "base_multiplier": 1.0, "max_multiplier": 1.5})
    result = c.evaluate(samples=50, wins=49, mean_net_bps=20, drawdown_pct=0, context_key="latency|BTC/USDT|trend|15")
    assert result.eligible is False
    assert result.multiplier == 0.5
    assert result.context_key == "latency|BTC/USDT|trend|15"


def test_risk_engine_accepts_context_for_sizing():
    risk = RiskEngine({
        "max_daily_loss_pct": -0.02,
        "max_weekly_loss_pct": -0.06,
        "kill_cooldown_seconds": 60,
        "max_symbol_loss_streak": 3,
        "cooldown_after_loss_seconds": 60,
        "risk_per_trade_pct": 0.005,
        "adaptive_risk": {"min_samples": 100, "base_multiplier": 1.0, "max_multiplier": 1.5},
    })
    sized, snapshot = risk.adaptive_position_notional(
        10_000, 0.01,
        samples=400, wins=320, mean_net_bps=6,
        strategy_id="latency", symbol="BTC/USDT", regime="trend", horizon_seconds=15,
    )
    assert snapshot.context_key == "latency|BTC/USDT|trend|15"
    assert sized > risk.position_notional(10_000, 0.01)
