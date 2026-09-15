from PC_ENGINE.radar.regime_engine import MarketRegimeEngine


def test_up_high_regime():
    regime = MarketRegimeEngine().classify([0.006, 0.005, 0.004, 0.003])
    assert regime.trend == "UP"
    assert regime.volatility == "HIGH"


def test_flat_low_regime():
    regime = MarketRegimeEngine().classify([0.0001, -0.0001, 0.0002, -0.0001])
    assert regime.trend == "FLAT"
    assert regime.volatility == "LOW"
