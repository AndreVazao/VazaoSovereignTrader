from PC_ENGINE.radar.evidence_ledger import EvidenceLedger
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


def test_durable_outcome_gate_requires_matching_candidate_version_and_regime():
    book = ChampionChallengerBook()
    book.register(candidate("challenger"))
    rows = []
    for index in range(60):
        rows.append({
            "candidate_id": "challenger", "version": "1.0", "strategy": "paper_strategy",
            "symbol": "BTC/USDT", "regime": "TREND", "entry_timestamp_ms": index * 600_000 + 1,
            "exit_timestamp_ms": index * 600_000 + 1000, "horizon_ms": 1000,
            "action": "BUY", "gross_bps": 50.0, "cost_bps": 28.0, "net_bps": 22.0,
            "risk_authorized": True, "paper_only": True,
        })
    decision, metrics, stress = book.assess_outcomes(
        "challenger", rows, costs_bps=(10.0, 20.0, 30.0),
        min_cost_scenarios=3, min_samples=30, min_folds=2,
        min_mean_net_bps=0.0, min_lower_ci_bps=0.0,
    )
    assert decision.eligible is True
    assert metrics is not None and metrics.samples == 60
    assert len(stress) == 3
    assert book.champion is None


def test_durable_outcome_gate_ignores_unauthorized_rows():
    book = ChampionChallengerBook()
    book.register(candidate("challenger"))
    rows = [{
        "candidate_id": "challenger", "version": "1.0", "strategy": "paper_strategy",
        "symbol": "BTC/USDT", "regime": "TREND", "entry_timestamp_ms": 1000,
        "exit_timestamp_ms": 2000, "horizon_ms": 1000, "action": "BUY",
        "gross_bps": 100.0, "cost_bps": 28.0, "net_bps": 72.0,
        "risk_authorized": False, "paper_only": True,
    }]
    decision, metrics, _ = book.assess_outcomes(
        "challenger", rows, min_samples=1, min_folds=1
    )
    assert decision.eligible is False
    assert metrics is None


def test_unified_evidence_gate_requires_both_durable_outcomes_and_chronological_oos(tmp_path):
    book = ChampionChallengerBook()
    book.register(candidate("challenger"))
    outcome_rows = []
    for index in range(60):
        outcome_rows.append({
            "candidate_id": "challenger", "version": "1.0", "strategy": "paper_strategy",
            "symbol": "BTC/USDT", "regime": "TREND",
            "entry_timestamp_ms": index * 600_000 + 1,
            "exit_timestamp_ms": index * 600_000 + 1000, "horizon_ms": 1000,
            "action": "BUY", "gross_bps": 50.0, "cost_bps": 28.0, "net_bps": 22.0,
            "risk_authorized": True, "paper_only": True,
        })
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

    decision = book.assess_unified_evidence(
        "challenger",
        states,
        outcome_rows,
        costs_bps=(10.0, 20.0, 30.0),
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
        min_samples=30,
        min_folds=2,
        evidence_ledger_path=str(tmp_path / "evidence.jsonl"),
    )

    assert decision.eligible is False
    assert "chronological OOS gate failed" in decision.reason
    assert len(book.audit) == 1
    records = EvidenceLedger.load(tmp_path / "evidence.jsonl")
    assert len(records) == 1
    assert records[0].candidate_id == "challenger"
    assert records[0].version == "1.0"
    assert records[0].eligible is False
    assert records[0].durable_outcome.scenarios == 3
    assert records[0].chronological_oos.status == "FAIL"
    assert book.champion is None


def test_unified_evidence_gate_does_not_accept_wrong_candidate_version():
    book = ChampionChallengerBook()
    book.register(candidate("challenger"))
    rows = [{
        "candidate_id": "challenger", "version": "2.0", "strategy": "paper_strategy",
        "symbol": "BTC/USDT", "regime": "TREND", "entry_timestamp_ms": 1000,
        "exit_timestamp_ms": 2000, "horizon_ms": 1000, "action": "BUY",
        "gross_bps": 100.0, "cost_bps": 28.0, "net_bps": 72.0,
        "risk_authorized": True, "paper_only": True,
    }]
    decision = book.assess_unified_evidence(
        "challenger",
        [],
        rows,
        min_samples=1,
        min_folds=1,
        min_cost_scenarios=1,
        costs_bps=(28.0,),
        train_size=2,
        test_size=1,
        horizons_ms=(1000,),
    )
    assert decision.eligible is False
    assert "durable outcome gate failed" in decision.reason
    assert book.champion is None
