from PC_ENGINE.radar.evidence_outcomes import EvidenceOutcomeEngine


def state(ts, price, regime="TREND"):
    return {
        "symbol": "BTC/USDT",
        "timestamp_ms": ts,
        "price": price,
        "regime": regime,
        "strategy_evidence": {
            "candlestick": {
                "patterns": [
                    {"name": "bullish_engulfing", "direction": "BUY", "score": 0.86},
                ]
            },
            "amd_phase": {
                "reason": "phase: MANIPULATION; sweep: LOW",
                "score": 0.7,
            },
        },
    }


def test_pattern_outcome_is_net_of_cost_and_regime_scoped():
    states = [state(1000, 100), state(2000, 101), state(3000, 102), state(4000, 103)]
    engine = EvidenceOutcomeEngine(cost_bps=10, min_samples=2, min_mean_net_bps=0, min_win_rate=0.5)
    stats = engine.evaluate(states, horizons_ms=(1000,))
    candle = next(item for item in stats if item.evidence_type == "candlestick")
    amd = next(item for item in stats if item.evidence_type == "amd_phase")
    assert candle.samples == 3
    assert candle.mean_net_bps > 80
    assert candle.eligible is True
    assert amd.samples == 3
    assert amd.eligible is True
    assert candle.regime == "TREND"


def test_bearish_evidence_is_scored_in_reverse():
    states = [
        {
            **state(1000, 100, "RANGE"),
            "strategy_evidence": {
                "candlestick": {
                    "patterns": [
                        {"name": "bearish_engulfing", "direction": "SELL", "score": -0.86}
                    ]
                }
            },
        },
        state(2000, 99, "RANGE"),
        state(3000, 98, "RANGE"),
    ]
    stats = EvidenceOutcomeEngine(cost_bps=10, min_samples=1).evaluate(states, horizons_ms=(1000,))
    candle = next(item for item in stats if item.evidence_name == "bearish_engulfing")
    assert candle.mean_net_bps > 80
