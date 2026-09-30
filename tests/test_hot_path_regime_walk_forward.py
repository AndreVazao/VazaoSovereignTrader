import json

from PC_ENGINE.radar.hot_path_regime_walk_forward import build_regime_walk_forward_report


def _row(i: int, realized: float, regime: str):
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
        "realized_response_bps": realized + 1.0,
        "market_regime": regime,
        "outcome_local_ts_ms": 1_000 + i * 1_000,
        "outcome_id": f"regime-{i}",
    }


def test_regime_walk_forward_keeps_test_after_train_and_stratifies_observed_regimes(tmp_path):
    source = tmp_path / "outcomes.jsonl"
    rows = [
        _row(0, 1.0, "RANGING"),
        _row(1, 1.0, "TRENDING"),
        _row(2, 2.0, "RANGING"),
        _row(3, 2.0, "TRENDING"),
        _row(4, -1.0, "RANGING"),
        _row(5, -2.0, "TRENDING"),
    ]
    source.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

    report = build_regime_walk_forward_report(
        source, train_size=2, test_size=2, min_test_samples=2
    )

    assert report["paper_only"] is True
    assert report["execution_authorized"] is False
    assert report["fold_count"] == 2

    first = report["folds"][0]
    assert first["train_end_ms"] < first["test_start_ms"]
    assert first["observed_market_regimes"] == ["RANGING", "TRENDING"]
    stats = {row["market_regime"]: row for row in first["regime_test_stats"]}
    assert stats["RANGING"]["test_mean_realized_net_bps"] == 2.0
    assert stats["TRENDING"]["test_mean_realized_net_bps"] == 2.0


def test_regime_walk_forward_uses_bootstrap_for_sufficient_timestamped_groups(tmp_path):
    source = tmp_path / "outcomes.jsonl"
    rows = [_row(i, float(i % 3 - 1), "TRENDING") for i in range(16)]
    source.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

    report = build_regime_walk_forward_report(
        source, train_size=8, test_size=8, min_test_samples=8
    )

    stat = report["folds"][0]["regime_test_stats"][0]
    assert stat["ci95_method"] == "moving_block_bootstrap"
    assert stat["bootstrap_replicates"] == 1000
    assert stat["bootstrap_block_length"] >= 2


def test_regime_walk_forward_preserves_unclassified_regime_without_inference(tmp_path):
    source = tmp_path / "outcomes.jsonl"
    rows = [_row(i, 1.0, "") for i in range(4)]
    for row in rows:
        row.pop("market_regime")
    source.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

    report = build_regime_walk_forward_report(
        source, train_size=2, test_size=2, min_test_samples=2
    )

    assert report["folds"][0]["observed_market_regimes"] == ["UNCLASSIFIED"]
    assert report["folds"][0]["regime_test_stats"][0]["market_regime"] == "UNCLASSIFIED"
