from PC_ENGINE.core.confluence import ConfluenceEngine
from PC_ENGINE.radar.lead_lag_signal import PaperLeadLagSignal
from PC_ENGINE.radar.regime_engine import MarketRegime


def test_single_source_cannot_trigger_order_action():
    result = ConfluenceEngine().evaluate(
        symbol="BTC/USDT",
        technical_action="BUY",
        technical_strength=1.0,
    )
    assert result.action == "HOLD"
    assert result.paper_only is True


def test_bullish_confluence_can_reach_buy():
    result = ConfluenceEngine().evaluate(
        symbol="BTC/USDT",
        technical_action="BUY",
        technical_strength=0.9,
        pattern_bias=0.8,
        radar_pressure=0.7,
        lead_lag_signals=[
            PaperLeadLagSignal("BTC/USDT", "okx", "binance", "UP", 500, 5.0, 0.9, 200)
        ],
        regime=MarketRegime("UP_NORMAL", "UP", "NORMAL", 0.9),
    )
    assert result.action == "BUY"
    assert result.score > 0.35


def test_conflict_reduces_score():
    result = ConfluenceEngine().evaluate(
        symbol="BTC/USDT",
        technical_action="BUY",
        technical_strength=0.9,
        pattern_bias=-0.9,
        radar_pressure=-0.8,
        lead_lag_signals=[
            PaperLeadLagSignal("BTC/USDT", "okx", "binance", "DOWN", 500, 5.0, 0.9, 200)
        ],
        regime=MarketRegime("UP_NORMAL", "UP", "NORMAL", 0.9),
    )
    assert result.contradictions
    assert result.action == "HOLD"
