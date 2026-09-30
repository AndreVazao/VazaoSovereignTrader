# Path: tests/test_hot_path.py
from __future__ import annotations

from PC_ENGINE.radar.hot_path import HotPathLeadLagEngine
from PC_ENGINE.radar.websocket_radar import MarketEvent


def event(exchange: str, price: float, ts: int, before: float | None = None) -> MarketEvent:
    return MarketEvent(
        exchange=exchange,
        symbol="BTC/USDT",
        price=price,
        quantity=1.0,
        side="BUY",
        exchange_ts_ms=ts,
        local_ts_ms=ts,
        local_receive_latency_ms=5,
        price_before=before,
    )


def test_hot_path_requires_learned_expectancy_and_positive_net_edge():
    engine = HotPathLeadLagEngine(
        exchanges=["binance", "coinbase"],
        min_move_bps=5,
        min_expected_net_bps=2,
        fee_bps_round_trip=4,
        slippage_bps_round_trip=2,
        latency_bps_per_100ms=0,
    )
    engine.set_expectancy(
        symbol="BTC/USDT",
        leader="binance",
        follower="coinbase",
        direction="UP",
        expected_response_bps=10,
    )

    assert engine.on_market_event(event("coinbase", 100.0, 1000)) is None
    assert engine.on_market_event(event("binance", 100.0, 1000)) is None
    opportunity = engine.on_market_event(event("binance", 100.1, 1100, 100.0))

    assert opportunity is not None
    assert opportunity.expected_net_bps == 4
    assert opportunity.paper_only is True
    assert opportunity.execution_allowed is False


def test_hot_path_rejects_stale_follower():
    engine = HotPathLeadLagEngine(
        exchanges=["binance", "coinbase"],
        stale_after_ms=50,
        min_move_bps=5,
        min_expected_net_bps=0,
        fee_bps_round_trip=0,
        slippage_bps_round_trip=0,
    )
    engine.set_expectancy(
        symbol="BTC/USDT",
        leader="binance",
        follower="coinbase",
        direction="UP",
        expected_response_bps=10,
    )

    engine.on_market_event(event("coinbase", 100.0, 1000))
    engine.on_market_event(event("binance", 100.0, 1000))
    assert engine.on_market_event(event("binance", 100.1, 1200, 100.0)) is None


def test_hot_path_snapshot_is_observation_only():
    engine = HotPathLeadLagEngine(exchanges=["binance"])
    snapshot = engine.snapshot()
    assert snapshot["paper_only"] is True
    assert snapshot["execution_allowed"] is False
