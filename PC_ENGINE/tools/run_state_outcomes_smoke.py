from PC_ENGINE.radar.state_outcomes import StateOutcomeEngine

if __name__ == "__main__":
    states = [{"symbol": "BTC/USDT", "timestamp_ms": i * 5000, "price": 100.0 + i, "action": "BUY", "regime": "UP_NORMAL"} for i in range(40)]
    stats = StateOutcomeEngine(cost_bps=10, min_samples=1).evaluate(states, horizons_ms=(5000,))
    print(f"groups={len(stats)}")
    for stat in stats:
        print(stat)
