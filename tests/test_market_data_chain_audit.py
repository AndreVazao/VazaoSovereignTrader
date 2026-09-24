from __future__ import annotations

from types import SimpleNamespace

from PC_ENGINE.core.strategy import TrendEmaAtrStrategy
from PC_ENGINE.radar.market_radar import MarketRadar


def test_strategy_fails_closed_before_indicator_access_on_invalid_ohlcv():
    strategy = TrendEmaAtrStrategy({})

    signal = strategy.analyse(
        "BTC/USDT",
        [[1_700_000_000_000, 100.0, 101.0, 99.0, float("nan"), 10.0]],
    )

    assert signal.action == "HOLD"
    assert signal.strength == 0.0
    assert "quality gate" in signal.reason


def test_radar_rejects_impossible_bid_ask_observation(tmp_path):
    radar = MarketRadar.__new__(MarketRadar)
    radar.exchanges = ["fake"]
    radar.symbols = ["BTC/USDT"]
    radar.data_dir = tmp_path
    radar.clients = {
        "fake": SimpleNamespace(
            fetch_ticker=lambda symbol: {
                "last": 100.0,
                "bid": 101.0,
                "ask": 99.0,
                "baseVolume": 10.0,
                "timestamp": 1_700_000_000_000,
            }
        )
    }
    radar.previous = {}
    radar.last_pressure = {}
    radar.quality_rejections = 0

    snapshots, leads = radar.snapshot()

    assert snapshots == []
    assert leads == []
    assert radar.quality_rejections == 1


def test_radar_accepts_valid_observation_and_preserves_quality_boundary(tmp_path):
    radar = MarketRadar.__new__(MarketRadar)
    radar.exchanges = ["fake"]
    radar.symbols = ["BTC/USDT"]
    radar.data_dir = tmp_path
    radar.clients = {
        "fake": SimpleNamespace(
            fetch_ticker=lambda symbol: {
                "last": 100.0,
                "bid": 99.9,
                "ask": 100.1,
                "baseVolume": 10.0,
                "timestamp": 1_700_000_000_000,
            }
        )
    }
    radar.previous = {}
    radar.last_pressure = {}
    radar.quality_rejections = 0

    snapshots, leads = radar.snapshot()

    assert len(snapshots) == 1
    assert snapshots[0].price == 100.0
    assert leads == []
    assert radar.quality_rejections == 0
