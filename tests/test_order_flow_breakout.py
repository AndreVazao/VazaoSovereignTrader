from PC_ENGINE.core.order_flow_strategy import OrderFlowStrategy
from PC_ENGINE.core.breakout_strategy import BreakoutVolumeStrategy


def candles(prices, volume=1000):
    return [[i, p * 1.002, p * 0.998, p, p, volume] for i, p in enumerate(prices)]


def test_order_flow_buy_imbalance():
    events = [{"price": 100, "quantity": 1, "side": "BUY"}] * 40 + [{"price": 100, "quantity": 0.2, "side": "SELL"}] * 10
    result = OrderFlowStrategy({"min_trades": 20}).analyse(events)
    assert result.action == "BUY"
    assert result.imbalance > 0


def test_order_flow_holds_without_enough_trades():
    events = [{"price": 100, "quantity": 1, "side": "BUY"}] * 5
    result = OrderFlowStrategy({"min_trades": 20}).analyse(events)
    assert result.action == "HOLD"


def test_breakout_requires_volume():
    prices = [100 + i * 0.1 for i in range(25)] + [103]
    result = BreakoutVolumeStrategy({"lookback": 20, "min_volume_ratio": 1.2}).analyse(candles(prices, 2000))
    assert result.action in {"BUY", "HOLD"}


def test_breakout_holds_without_volume_confirmation():
    prices = [100.0] * 20 + [102.0]
    result = BreakoutVolumeStrategy({"lookback": 10, "min_volume_ratio": 2.0}).analyse(candles(prices, 1000))
    assert result.action == "HOLD"
