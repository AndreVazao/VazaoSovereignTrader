from PC_ENGINE.radar.state_outcomes import StateOutcomeEngine


def _states():
    rows = []
    for i in range(40):
        rows.append({
            "symbol": "BTC/USDT",
            "timestamp_ms": i * 5000,
            "price": 100.0 + i,
            "action": "BUY",
            "regime": "UP_NORMAL",
        })
    return rows


def test_outcome_engine_is_net_of_costs_and_aggregates():
    stats = StateOutcomeEngine(cost_bps=10, min_samples=1).evaluate(_states(), horizons_ms=(5000,))
    assert stats
    row = stats[0]
    assert row.samples > 0
    assert row.mean_net_bps > 0
    assert row.eligible is True


def test_sell_outcome_reverses_direction():
    states = _states()
    for row in states:
        row["action"] = "SELL"
    stats = StateOutcomeEngine(cost_bps=10, min_samples=1).evaluate(states, horizons_ms=(5000,))
    assert stats
    assert stats[0].mean_net_bps < 0
