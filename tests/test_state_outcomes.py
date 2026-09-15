from PC_ENGINE.radar.state_outcomes import StateOutcomeEngine


def _states(action="BUY"):
    return [{"symbol": "BTC/USDT", "timestamp_ms": i * 5000, "price": 100.0 + i, "action": action, "regime": "UP_NORMAL"} for i in range(40)]


def test_outcome_engine_is_net_of_costs_and_aggregates():
    stats = StateOutcomeEngine(cost_bps=10, min_samples=1).evaluate(_states(), horizons_ms=(5000,))
    assert stats and stats[0].samples > 0
    assert stats[0].mean_net_bps > 0
    assert stats[0].eligible is True


def test_sell_outcome_reverses_direction():
    stats = StateOutcomeEngine(cost_bps=10, min_samples=1).evaluate(_states("SELL"), horizons_ms=(5000,))
    assert stats and stats[0].mean_net_bps < 0
