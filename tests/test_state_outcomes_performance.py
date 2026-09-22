from __future__ import annotations

from PC_ENGINE.radar.state_outcomes import StateOutcomeEngine


def test_state_outcomes_handles_large_history_and_horizon_index():
    states = []
    start = 1_700_000_000_000
    for i in range(3000):
        states.append({
            "symbol": "BTC/USDT",
            "timestamp_ms": start + i * 1000,
            "price": 100.0 + i * 0.01,
            "action": "BUY",
            "regime": "TREND_UP",
        })
    stats = StateOutcomeEngine(min_samples=30, cost_bps=0.0).evaluate(states, horizons_ms=(1000, 5000))
    assert stats
    one_second = next(row for row in stats if row.horizon_ms == 1000)
    assert one_second.samples > 1000
    assert one_second.mean_net_bps > 0


def test_state_outcomes_keeps_symbols_isolated():
    states = []
    start = 1_700_000_000_000
    for i in range(100):
        states.extend([
            {"symbol": "BTC/USDT", "timestamp_ms": start + i * 1000, "price": 100 + i, "action": "BUY", "regime": "TREND_UP"},
            {"symbol": "ETH/USDT", "timestamp_ms": start + i * 1000, "price": 200 - i, "action": "BUY", "regime": "TREND_DOWN"},
        ])
    stats = StateOutcomeEngine(min_samples=30).evaluate(states, horizons_ms=(1000,))
    btc = next(row for row in stats if row.symbol == "BTC/USDT")
    eth = next(row for row in stats if row.symbol == "ETH/USDT")
    assert btc.mean_net_bps > 0
    assert eth.mean_net_bps < 0
