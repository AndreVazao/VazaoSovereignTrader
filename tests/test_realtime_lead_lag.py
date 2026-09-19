from PC_ENGINE.market_events.normalized import MarketEventFactory
from PC_ENGINE.radar.realtime_lead_lag import RealtimeLeadLagEngine


def event(venue: str, price: float, ts_ms: int):
    return MarketEventFactory.create(
        venue=venue, symbol="BTC/USDT", event_type="trade",
        exchange_ts_ms=ts_ms, provider_ts_ms=ts_ms,
        receive_wall_ns=1_700_000_000_000_000_000 + ts_ms * 1_000_000,
        receive_ns=ts_ms * 1_000_000, process_ns=ts_ms * 1_000_000 + 1000,
        price=price, raw_source="websocket",
    )


def test_detects_directional_leader_then_follower():
    engine = RealtimeLeadLagEngine(max_lag_ms=750, min_move_bps=5, min_confidence=0.6)
    assert engine.observe(event("binance", 100.0, 1000)) is None
    assert engine.observe(event("okx", 100.0, 1001)) is None
    assert engine.observe(event("binance", 100.10, 1100)) is None
    signal = engine.observe(event("okx", 100.10, 1105))
    assert signal is not None
    assert signal.leader == "binance"
    assert signal.follower == "okx"
    assert signal.direction == "UP"
    assert signal.lag_ms == 5


def test_rejects_same_direction_outside_window():
    engine = RealtimeLeadLagEngine(max_lag_ms=10, min_move_bps=5)
    engine.observe(event("binance", 100.0, 1000))
    engine.observe(event("okx", 100.0, 1001))
    engine.observe(event("binance", 100.10, 1100))
    assert engine.observe(event("okx", 100.10, 1120)) is None
