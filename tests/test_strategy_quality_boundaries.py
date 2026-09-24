from __future__ import annotations

from PC_ENGINE.core.breakout_strategy import BreakoutVolumeStrategy
from PC_ENGINE.core.mean_reversion_strategy import MeanReversionStrategy
from PC_ENGINE.core.momentum_strategy import MultiTimeframeMomentumStrategy
from PC_ENGINE.core.order_flow_strategy import OrderFlowStrategy


def candles(n: int = 40) -> list[list[float]]:
    return [[1_700_000_000_000 + i * 60_000, 100, 101, 99, 100 + i * 0.1, 100] for i in range(n)]


def test_momentum_blocks_invalid_frame_data():
    data = candles(40)
    data[10][4] = float("nan")
    strategy = MultiTimeframeMomentumStrategy()
    evidence = strategy.analyse({"5m": data, "15m": candles(40)})
    assert evidence.action == "HOLD"
    assert evidence.score == 0.0


def test_mean_reversion_blocks_invalid_ohlcv():
    data = candles(40)
    data[-1][2] = 90
    strategy = MeanReversionStrategy()
    evidence = strategy.analyse(data, "RANGE")
    assert evidence.action == "HOLD"
    assert "quality gate" in evidence.reason


def test_breakout_blocks_invalid_ohlcv():
    data = candles(40)
    data[-1][0] = data[-2][0]
    strategy = BreakoutVolumeStrategy()
    evidence = strategy.analyse(data)
    assert evidence.action == "HOLD"
    assert "quality gate" in evidence.reason


def test_order_flow_ignores_malformed_events_without_creating_evidence():
    strategy = OrderFlowStrategy({"min_trades": 2})
    evidence = strategy.analyse([
        {"price": "nan", "quantity": 10, "side": "BUY"},
        {"price": 100, "quantity": 1, "side": "BUY"},
        {"price": 100, "quantity": 1, "side": "SELL"},
        {"price": 100, "quantity": 1, "side": "SELL"},
    ])
    assert evidence.action == "HOLD"
    assert evidence.score == 0.0
    assert evidence.trades == 3
