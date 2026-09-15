from PC_ENGINE.radar.market_state import MarketStateStore, build_market_state
from PC_ENGINE.radar.regime_engine import MarketRegimeEngine


class Score:
    score = 0.42
    confidence = 0.81
    action = "BUY"


def test_build_market_state_normalizes_evidence(tmp_path):
    regime = MarketRegimeEngine().classify([0.002, 0.003, 0.001])
    state = build_market_state(
        symbol="BTC/USDT",
        price=100000,
        regime=regime,
        technical_score=2.0,
        candlestick_bias=-2.0,
        radar_pressure=0.25,
        lead_lag_score=0.1,
        momentum_score=0.2,
        mean_reversion_score=-0.2,
        order_flow_score=0.3,
        breakout_score=0.4,
        derivatives_score=-0.3,
        confluence=Score(),
        timestamp_ms=123,
    )
    assert state.symbol == "BTC/USDT"
    assert state.technical_score == 1.0
    assert state.candlestick_bias == -1.0
    assert state.confluence_score == 0.42
    assert state.action == "BUY"


def test_market_state_store_round_trip(tmp_path):
    store = MarketStateStore(str(tmp_path))
    regime = MarketRegimeEngine().classify([0.001])
    state = build_market_state(
        symbol="ETH/USDT", price=3000, regime=regime,
        technical_score=0.2, candlestick_bias=0.1, radar_pressure=0.0,
        lead_lag_score=0.0, momentum_score=0.1, mean_reversion_score=0.0,
        order_flow_score=0.2, breakout_score=0.0, derivatives_score=0.0,
        confluence=Score(), timestamp_ms=456,
    )
    store.append(state)
    assert store.snapshot("ETH/USDT")["timestamp_ms"] == 456
    assert store.recent("BTC/USDT") == []
