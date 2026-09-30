import json

from PC_ENGINE.radar.hot_path_oos_robustness import build_oos_robustness_report


def _row(i: int, realized: float):
    return {
        "status": "COMPLETED",
        "paper_only": True,
        "orders_submitted": False,
        "symbol": "BTC/USDT",
        "leader": "binance",
        "follower": "coinbase",
        "direction": "UP",
        "horizon_ms": 500,
        "expected_net_bps": 1.0,
        "realized_net_bps": realized,
        "outcome_local_ts_ms": 1_000 + i * 1_000,
        "outcome_id": f"robust-{i}",
    }


def test_oos_robustness_keeps_cost_stress_out_of_observed_results(tmp_path):
    source = tmp_path / "outcomes.jsonl"
    rows = [_row(i, 2.0) for i in range(8)]
    source.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

    report = build_oos_robustness_report(
        source,
        train_size=4,
        test_size=4,
        min_test_samples=4,
        extra_cost_scenarios_bps=(0.0, 1.0, 2.0),
        monte_carlo_replicates=500,
    )

    assert report["paper_only"] is True
    assert report["orders_submitted"] is False
    assert report["execution_authorized"] is False
    assert [row["extra_cost_bps"] for row in report["scenarios"]] == [0.0, 1.0, 2.0]
    assert report["scenarios"][0]["mean_adjusted_realized_net_bps"] == 2.0
    assert report["scenarios"][2]["mean_adjusted_realized_net_bps"] == 0.0


def test_oos_robustness_uses_chronological_oos_only(tmp_path):
    source = tmp_path / "outcomes.jsonl"
    rows = [_row(i, 1.0 if i < 4 else -1.0) for i in range(8)]
    source.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

    report = build_oos_robustness_report(
        source,
        train_size=4,
        test_size=4,
        min_test_samples=4,
        extra_cost_scenarios_bps=(0.0,),
        monte_carlo_replicates=500,
    )

    scenario = report["scenarios"][0]
    assert scenario["mean_adjusted_realized_net_bps"] == -1.0
    assert scenario["positive_fold_rate"] == 0.0
    assert scenario["monte_carlo_probability_mean_positive"] == 0.0


def test_oos_robustness_bootstrap_is_deterministic(tmp_path):
    source = tmp_path / "outcomes.jsonl"
    rows = [_row(i, float((i % 3) - 1)) for i in range(12)]
    source.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

    kwargs = dict(
        train_size=6,
        test_size=6,
        min_test_samples=6,
        extra_cost_scenarios_bps=(0.5,),
        monte_carlo_replicates=500,
    )
    first = build_oos_robustness_report(source, **kwargs)
    second = build_oos_robustness_report(source, **kwargs)

    assert first["scenarios"] == second["scenarios"]
    assert first["scenarios"][0]["monte_carlo_method"] == "moving_block_bootstrap"
