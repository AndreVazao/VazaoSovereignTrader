from PC_ENGINE.core.risk import RiskEngine


def _settings():
    return {
        "max_daily_loss_pct": -0.02,
        "max_weekly_loss_pct": -0.06,
        "kill_cooldown_seconds": 60,
        "max_symbol_loss_streak": 3,
        "cooldown_after_loss_seconds": 60,
        "risk_per_trade_pct": 0.005,
        "adaptive_risk": {
            "enabled": True,
            "min_samples": 100,
            "min_win_rate": 0.55,
            "min_mean_net_bps": 2.0,
            "base_multiplier": 1.0,
            "max_multiplier": 1.5,
        },
    }


def test_risk_sizing_does_not_scale_without_evidence():
    risk = RiskEngine(_settings())
    base = risk.position_notional(10_000, 0.01)
    sized, snapshot = risk.adaptive_position_notional(
        10_000, 0.01, samples=20, wins=19, mean_net_bps=10
    )
    assert sized == base * 0.5
    assert snapshot.eligible is False


def test_risk_sizing_scales_after_validated_positive_edge():
    risk = RiskEngine(_settings())
    base = risk.position_notional(10_000, 0.01)
    sized, snapshot = risk.adaptive_position_notional(
        10_000, 0.01, samples=400, wins=320, mean_net_bps=6,
        lower_ci_bps=2.0, evidence_age_ms=0, regime_stability=1.0,
    )
    assert sized > base
    assert sized <= base * 1.5
    assert snapshot.eligible is True
