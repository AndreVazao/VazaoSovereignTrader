from PC_ENGINE.radar.champion_challenger import (
    CandidateObservation,
    CandidateSpec,
    ChampionChallengerBook,
)


def candidate(cid: str) -> CandidateSpec:
    return CandidateSpec(
        cid,
        "1.0",
        "paper_strategy",
        (("cost_model", "stress"),),
        "candlestick",
        "bullish_engulfing",
        "BTC/USDT",
        "TREND",
        1000,
    )


def record(book: ChampionChallengerBook, cid: str, base: float) -> None:
    for index in range(6):
        book.record(
            CandidateObservation(
                candidate_id=cid,
                version="1.0",
                symbol="BTC/USDT",
                timestamp_ms=1000 + index,
                action="BUY",
                net_bps=base + index,
                risk_authorized=True,
                latency_ms=10 + index,
                slippage_bps=1.0,
            )
        )


def test_champion_and_challenger_are_isolated_and_use_same_observation_contract():
    book = ChampionChallengerBook()
    book.register(candidate("champion"))
    book.register(candidate("challenger"))
    book.set_champion("champion")
    record(book, "champion", 1.0)
    record(book, "challenger", 0.5)

    metrics = {row.candidate_id: row for row in book.evaluate(min_samples=6)}
    assert set(metrics) == {"champion", "challenger"}
    assert metrics["champion"].samples == metrics["challenger"].samples == 6
    assert metrics["champion"].mean_latency_ms == metrics["challenger"].mean_latency_ms
    assert book.champion is not None
    assert book.champion.candidate_id == "champion"


def test_promotion_assessment_requires_cost_stress_and_never_changes_champion():
    book = ChampionChallengerBook()
    book.register(candidate("champion"))
    book.register(candidate("challenger"))
    book.set_champion("champion")
    record(book, "challenger", 1.0)

    blocked = book.assess(
        "challenger",
        min_samples=6,
        min_mean_net_bps=0.0,
        max_drawdown_bps=100.0,
        required_stress_scenarios=3,
        validated_stress_scenarios=2,
    )
    assert blocked.eligible is False
    assert "cost-stress gate failed" in blocked.reason
    assert book.champion.candidate_id == "champion"

    eligible = book.assess(
        "challenger",
        min_samples=6,
        min_mean_net_bps=0.0,
        max_drawdown_bps=100.0,
        required_stress_scenarios=3,
        validated_stress_scenarios=3,
    )
    assert eligible.eligible is True
    assert book.champion.candidate_id == "champion"


def test_risk_violation_blocks_candidate_even_with_positive_results():
    book = ChampionChallengerBook()
    book.register(candidate("challenger"))
    for index in range(6):
        book.record(
            CandidateObservation(
                candidate_id="challenger",
                version="1.0",
                symbol="BTC/USDT",
                timestamp_ms=2000 + index,
                action="BUY",
                net_bps=2.0,
                risk_authorized=False,
                risk_violation=True,
            )
        )
    decision = book.assess(
        "challenger",
        min_samples=6,
        max_risk_violations=0,
        required_stress_scenarios=0,
        validated_stress_scenarios=0,
    )
    assert decision.eligible is False
    assert "base PAPER metrics gate failed" in decision.reason


def test_evidence_assessment_requires_shared_oos_cost_stress_evidence():
    book = ChampionChallengerBook()
    book.register(candidate("challenger"))
    record(book, "challenger", 1.0)
    states = [
        {
            "symbol": "BTC/USDT",
            "timestamp_ms": index * 1000 + 1,
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
    decision = book.assess_with_evidence(
        "challenger",
        states,
        costs_bps=(10.0, 50.0, 100.0),
        min_cost_scenarios=3,
        validator_kwargs={
            "min_train_samples": 3,
            "min_train_mean_net_bps": 0.0,
            "min_train_win_rate": 0.5,
            "min_oos_samples": 2,
            "min_oos_folds": 2,
        },
        train_size=8,
        test_size=4,
        horizons_ms=(1000,),
        min_samples=6,
    )
    assert decision.eligible is False
    assert "OOS cost-stress evidence gate failed" in decision.reason
    assert book.champion is None
