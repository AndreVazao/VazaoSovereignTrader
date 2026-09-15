from PC_ENGINE.core.mean_reversion_strategy import MeanReversionStrategy
from PC_ENGINE.core.momentum_strategy import MultiTimeframeMomentumStrategy


def candles(prices):
    return [[i, p * 1.002, p * 0.998, p, p, 1000] for i, p in enumerate(prices)]


def test_momentum_requires_alignment():
    prices = [100 + i * 0.4 for i in range(40)]
    strategy = MultiTimeframeMomentumStrategy({"min_aligned_timeframes": 2})
    result = strategy.analyse({"5m": candles(prices), "15m": candles(prices), "1h": candles(list(reversed(prices)))})
    assert result.action == "BUY"
    assert result.score > 0


def test_mean_reversion_buy_when_below_vwap_in_flat_regime():
    prices = [100.0] * 35 + [99.2]
    strategy = MeanReversionStrategy({"vwap_period": 30, "min_deviation_pct": 0.002, "max_deviation_pct": 0.03})
    result = strategy.analyse(candles(prices), "FLAT_NORMAL")
    assert result.action == "BUY"
    assert result.score > 0


def test_mean_reversion_avoids_high_volatility_regime():
    prices = [100 + (i % 2) * 3 for i in range(35)]
    strategy = MeanReversionStrategy()
    result = strategy.analyse(candles(prices), "FLAT_HIGH")
    assert result.action == "HOLD"
