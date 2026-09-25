from PC_ENGINE.radar.evidence_stress import EvidenceStatisticalStressTester


def make_states():
    return [
        {
            "symbol": "BTC/USDT",
            "timestamp_ms": index * 1000,
            "price": 100.0 + index,
            "regime": "TREND",
            "strategy_evidence": {
                "candlestick": {
                    "patterns": [
                        {"name": "bullish_engulfing", "direction": "BUY", "score": 0.9}
                    ]
                }
            },
        }
        for index in range(20)
    ]


def test_cost_stress_runs_same_oos_protocol_at_multiple_costs():
    tester = EvidenceStatisticalStressTester(
        costs_bps=(10.0, 50.0, 100.0),
        validator_kwargs={
            "min_train_samples": 3,
            "min_train_mean_net_bps": 0,
            "min_train_win_rate": 0.5,
            "min_oos_samples": 2,
            "min_oos_folds": 2,
        },
    )
    stats = tester.validate(make_states(), train_size=8, test_size=4, horizons_ms=(1000,))
    rows = [row for row in stats if row.evidence_name == "bullish_engulfing"]
    assert {row.cost_bps for row in rows} == {10.0, 50.0, 100.0}
    assert all(row.bootstrap_lower_ci_bps > 0 for row in rows if row.validated)


def test_cost_stress_robustness_requires_all_requested_scenarios():
    tester = EvidenceStatisticalStressTester(costs_bps=(10.0, 50.0))
    stats = tester.validate(
        make_states(),
        train_size=8,
        test_size=4,
        horizons_ms=(1000,),
    )
    robust = tester.robustness(stats, min_cost_scenarios=2)
    key = ("candlestick", "bullish_engulfing", "BTC/USDT", "TREND", 1000)
    assert robust[key] is True
