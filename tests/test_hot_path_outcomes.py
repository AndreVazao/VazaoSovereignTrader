# Path: tests/test_hot_path_outcomes.py
from PC_ENGINE.radar.hot_path import HotPathLeadLagEngine
from PC_ENGINE.radar.hot_path_outcomes import HotPathOutcomeTracker
from PC_ENGINE.radar.websocket_radar import MarketEvent


def _event(exchange: str, price: float, ts: int) -> MarketEvent:
    return MarketEvent(
        exchange=exchange,
        symbol="BTC/USDT",
        price=price,
        quantity=1.0,
        side="BUY",
        exchange_ts_ms=ts,
        local_ts_ms=ts,
        local_receive_latency_ms=5,
        price_before=None,
    )


def _opportunity():
    detector = HotPathLeadLagEngine(
        exchanges=["binance", "coinbase"],
        min_move_bps=5,
        min_expected_net_bps=2,
        fee_bps_round_trip=4,
        slippage_bps_round_trip=2,
        latency_bps_per_100ms=0,
        horizon_ms=500,
    )
    detector.set_expectancy(
        symbol="BTC/USDT",
        leader="binance",
        follower="coinbase",
        direction="UP",
        expected_response_bps=10,
    )
    detector.on_market_event(_event("coinbase", 100.0, 1000))
    detector.on_market_event(_event("binance", 100.0, 1000))
    return detector.on_market_event(_event("binance", 100.1, 1100))


def test_outcome_tracker_waits_until_horizon_then_records_net_result():
    opportunity = _opportunity()
    assert opportunity is not None
    tracker = HotPathOutcomeTracker()
    assert tracker.register(opportunity)

    tracker.on_market_event(_event("coinbase", 100.1, 1500))
    assert tracker.drain_completed() == []

    tracker.on_market_event(_event("coinbase", 100.2, 1700))
    outcomes = tracker.drain_completed()
    assert len(outcomes) == 1
    outcome = outcomes[0]
    assert outcome["paper_only"] is True
    assert outcome["orders_submitted"] is False
    assert outcome["realized_response_bps"] > 19.0
    assert outcome["realized_net_bps"] > 13.0
    assert outcome["profitable_after_costs"] is True


def test_outcome_tracker_rejects_non_observational_opportunities():
    opportunity = _opportunity()
    assert opportunity is not None
    altered = type(opportunity)(
        **{**opportunity.__dict__, "execution_allowed": True}
    )
    tracker = HotPathOutcomeTracker()
    assert not tracker.register(altered)
    assert tracker.snapshot()["pending"] == 0


def test_outcome_tracker_is_bounded_and_observation_only():
    tracker = HotPathOutcomeTracker(max_pending=1)
    opportunity = _opportunity()
    assert opportunity is not None
    assert tracker.register(opportunity)
    assert tracker.snapshot()["paper_only"] is True
    assert tracker.snapshot()["orders_submitted"] is False


def test_completed_outcomes_remain_buffered_until_persistence_is_acknowledged():
    opportunity = _opportunity()
    assert opportunity is not None
    tracker = HotPathOutcomeTracker()
    assert tracker.register(opportunity)
    tracker.on_market_event(_event("coinbase", 100.2, 1700))

    first_peek = tracker.peek_completed()
    second_peek = tracker.peek_completed()
    assert len(first_peek) == 1
    assert first_peek == second_peek
    assert tracker.snapshot()["completed_buffered"] == 1

    assert tracker.acknowledge_completed(1) == 1
    assert tracker.peek_completed() == []
    assert tracker.snapshot()["completed_buffered"] == 0
