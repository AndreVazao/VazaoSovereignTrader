from PC_ENGINE.radar.evidence_oos import EvidenceWalkForwardValidator


def make_states(prices, regimes=None):
    regimes = regimes or ["TREND"] * len(prices)
    return [
        {
            "symbol": "BTC/USDT",
            "timestamp_ms": index * 1000,
            "price": price,
            "regime": regimes[index],
            "strategy_evidence": {
                "candlestick": {
                    "patterns": [
                        {"name": "bullish_engulfing", "direction": "BUY", "score": 0.9}
                    ]
                }
            },
        }
        for index, price in enumerate(prices)
    ]


def test_persistent_edge_validates_only_on_unseen_folds():
    states = make_states([100 + index for index in range(20)])
    validator = EvidenceWalkForwardValidator(
        cost_bps=10,
        min_train_samples=3,
        min_train_mean_net_bps=0,
        min_train_win_rate=0.5,
        min_oos_samples=2,
        min_oos_folds=2,
    )
    folds, stats = validator.validate(
        states,
        train_size=8,
        test_size=4,
        horizons_ms=(1000,),
    )
    item = next(row for row in stats if row.evidence_name == "bullish_engulfing")
    assert len(folds) == 2
    assert item.folds >= 2
    assert item.samples >= 2
    assert item.mean_net_bps > 0
    assert item.validated is True


def test_in_sample_edge_does_not_validate_when_oos_reverses():
    prices = [100 + index for index in range(9)] + [108 - index for index in range(11)]
    states = make_states(prices)
    validator = EvidenceWalkForwardValidator(
        cost_bps=10,
        min_train_samples=3,
        min_train_mean_net_bps=0,
        min_train_win_rate=0.5,
        min_oos_samples=2,
        min_oos_folds=2,
    )
    _, stats = validator.validate(
        states,
        train_size=8,
        test_size=4,
        horizons_ms=(1000,),
    )
    item = next(row for row in stats if row.evidence_name == "bullish_engulfing")
    assert item.mean_net_bps < 0
    assert item.validated is False


def test_training_observation_touching_oos_boundary_is_purged():
    states = make_states([100 + index for index in range(10)])
    validator = EvidenceWalkForwardValidator(
        cost_bps=10,
        min_train_samples=4,
        min_train_mean_net_bps=0,
        min_train_win_rate=0.5,
        min_oos_samples=1,
        min_oos_folds=1,
    )
    folds, stats = validator.validate(
        states,
        train_size=4,
        test_size=2,
        horizons_ms=(1000,),
    )
    assert folds[0].train_eligible_groups == 0
    assert stats == []


def test_costs_can_turn_gross_oos_edge_into_failure():
    states = make_states([100.00, 101.00, 102.00, 103.00, 104.00, 105.00, 106.00, 106.01, 106.02, 106.03, 106.04, 106.05])
    validator = EvidenceWalkForwardValidator(
        cost_bps=10,
        min_train_samples=2,
        min_train_mean_net_bps=0,
        min_train_win_rate=0.5,
        min_oos_samples=1,
        min_oos_folds=1,
    )
    _, stats = validator.validate(
        states,
        train_size=6,
        test_size=3,
        horizons_ms=(1000,),
    )
    item = next(row for row in stats if row.evidence_name == "bullish_engulfing")
    assert item.mean_net_bps < 0
    assert item.validated is False

def test_bootstrap_ci_and_fold_stability_are_recorded():
    states = make_states([100 + index for index in range(20)])
    validator = EvidenceWalkForwardValidator(
        cost_bps=10,
        min_train_samples=3,
        min_train_mean_net_bps=0,
        min_train_win_rate=0.5,
        min_oos_samples=2,
        min_oos_folds=2,
    )
    _, stats = validator.validate(states, train_size=8, test_size=4, horizons_ms=(1000,))
    item = next(row for row in stats if row.evidence_name == "bullish_engulfing")
    assert item.bootstrap_lower_ci_bps > 0
    assert item.positive_fold_ratio == 1.0
    assert item.validated is True
