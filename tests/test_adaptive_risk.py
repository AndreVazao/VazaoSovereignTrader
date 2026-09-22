from PC_ENGINE.core.adaptive_risk import AdaptiveRiskController


def test_adaptive_risk_stays_conservative_without_enough_evidence():
    controller = AdaptiveRiskController({})
    result = controller.evaluate(samples=20, wins=18, mean_net_bps=10, drawdown_pct=0)
    assert not result.eligible
    assert result.multiplier == 0.5


def test_adaptive_risk_scales_only_after_statistically_confirmed_edge():
    controller = AdaptiveRiskController({"min_samples": 100})
    result = controller.evaluate(
        samples=400, wins=320, mean_net_bps=6, drawdown_pct=0.005,
        lower_ci_bps=1.0, evidence_age_ms=1000, regime_stability=0.9,
    )
    assert result.eligible
    assert 1.0 < result.multiplier <= 1.5


def test_drawdown_stale_and_unstable_evidence_block_risk_increase():
    controller = AdaptiveRiskController({"min_samples": 100})
    kwargs = dict(samples=400, wins=320, mean_net_bps=6, drawdown_pct=0,
                  lower_ci_bps=1.0, evidence_age_ms=1000, regime_stability=0.9)
    assert not controller.evaluate(**{**kwargs, "drawdown_pct": 0.02}).eligible
    assert not controller.evaluate(**{**kwargs, "evidence_age_ms": 86_400_001}).eligible
    assert not controller.evaluate(**{**kwargs, "regime_stability": 0.4}).eligible


def test_independent_negative_evidence_blocks_risk_increase():
    controller = AdaptiveRiskController({"min_samples": 100})
    result = controller.evaluate(
        samples=400, wins=320, mean_net_bps=6, drawdown_pct=0,
        lower_ci_bps=1.0, evidence_age_ms=1000, regime_stability=0.9,
        independent_samples=200, independent_mean_net_bps=-0.1,
    )
    assert not result.eligible


def test_disabling_adaptive_risk_keeps_base_multiplier():
    controller = AdaptiveRiskController({"enabled": False, "base_multiplier": 1.0, "max_multiplier": 1.5})
    result = controller.evaluate(samples=1000, wins=900, mean_net_bps=20, drawdown_pct=0)
    assert not result.eligible
    assert result.multiplier == 1.0
