from __future__ import annotations

from PC_ENGINE.radar.champion_outcomes import ChampionOutcomeAggregator


def _row(ts: int, gross: float, *, candidate="c", authorized=True, regime="TREND"):
    return {
        "candidate_id": candidate,
        "version": "1.0",
        "strategy": "momentum",
        "symbol": "BTC/USDT",
        "regime": regime,
        "entry_timestamp_ms": ts - 1000,
        "exit_timestamp_ms": ts,
        "horizon_ms": 1000,
        "action": "BUY",
        "gross_bps": gross,
        "cost_bps": 10.0,
        "net_bps": gross - 10.0,
        "risk_authorized": authorized,
        "paper_only": True,
    }


def test_aggregate_isolates_candidate_regime_and_authorization():
    rows = [
        _row(300_000 + i * 10_000, 20.0) for i in range(3)
    ] + [
        _row(600_000 + i * 10_000, 20.0, regime="RANGE") for i in range(3)
    ] + [
        _row(300_000 + i * 10_000, 100.0, candidate="other") for i in range(3)
    ] + [
        _row(300_000, 100.0, authorized=False)
    ]
    agg = ChampionOutcomeAggregator(min_samples=3, min_folds=2, bootstrap_samples=200)
    metrics = agg.aggregate(rows)
    assert {(m.candidate_id, m.regime) for m in metrics} == {
        ("c", "TREND"), ("c", "RANGE"), ("other", "TREND")
    }
    assert all(m.samples == 3 for m in metrics)


def test_stress_recomputes_net_from_gross_without_lookahead():
    rows = [_row(300_000 + i * 10_000, 40.0) for i in range(6)]
    agg = ChampionOutcomeAggregator(min_samples=6, min_folds=2, bootstrap_samples=200)
    stats = agg.stress(rows, costs_bps=(10.0, 35.0))
    by_cost = {s.cost_bps: s for s in stats}
    assert by_cost[10.0].mean_net_bps == 30.0
    assert by_cost[35.0].mean_net_bps == 5.0
    assert agg.robustness(stats, min_cost_scenarios=2)


def test_invalid_or_non_paper_outcomes_fail_closed():
    agg = ChampionOutcomeAggregator()
    row = _row(1000, 20.0)
    row["paper_only"] = False
    try:
        agg.aggregate([row])
    except ValueError:
        pass
    else:
        raise AssertionError("non-PAPER outcome must be rejected")


def test_negative_cost_scenario_fails_closed():
    agg = ChampionOutcomeAggregator()
    try:
        agg.stress([_row(1000, 20.0)], costs_bps=(-1.0,))
    except ValueError:
        pass
    else:
        raise AssertionError("negative cost scenario must be rejected")
