import json

from PC_ENGINE.radar.hot_path_walk_forward import build_walk_forward_report


def _row(i: int, realized: float, expected: float = 1.0):
    return {
        "status": "COMPLETED",
        "paper_only": True,
        "orders_submitted": False,
        "symbol": "BTC/USDT",
        "leader": "binance",
        "follower": "coinbase",
        "direction": "UP",
        "horizon_ms": 500,
        "expected_net_bps": expected,
        "realized_net_bps": realized,
        "realized_response_bps": realized + 5,
        "outcome_local_ts_ms": 1_000 + i * 1_000,
        "outcome_id": f"o-{i}",
    }


def test_walk_forward_uses_later_test_windows_only(tmp_path):
    source = tmp_path / "outcomes.jsonl"
    rows = [_row(i, 2.0 if i < 10 else 1.0) for i in range(20)]
    source.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    report = build_walk_forward_report(source, train_size=10, test_size=5, step=5, min_test_samples=5)
    stat = report["stats"][0]
    assert stat["folds"] == 2
    assert stat["usable_folds"] == 2
    first = stat["folds_detail"][0]
    assert first["train_end_ts_ms"] < first["test_start_ts_ms"]
    assert first["test_mean_realized_net_bps"] == 1.0
    assert first["test_passes_train_sign_gate"] is True
    assert report["execution_authorized"] is False


def test_walk_forward_deduplicates_and_rejects_untimestamped_rows(tmp_path):
    source = tmp_path / "outcomes.jsonl"
    valid = _row(0, 1.0)
    duplicate = dict(valid)
    invalid = dict(_row(1, 1.0))
    del invalid["outcome_local_ts_ms"]
    source.write_text(
        "\n".join(json.dumps(row) for row in [valid, duplicate, invalid]) + "\n",
        encoding="utf-8",
    )
    report = build_walk_forward_report(source, train_size=2, test_size=2)
    assert report["outcome_records_loaded"] == 3
    assert report["duplicate_outcomes_ignored"] == 1
    assert report["invalid_or_untimestamped_ignored"] == 1
    assert report["valid_timestamped_samples"] == 1


def test_walk_forward_separates_market_regimes(tmp_path):
    source = tmp_path / "outcomes.jsonl"
    rows = [
        {**_row(i, 1.0), "market_regime": "TRENDING"} for i in range(12)
    ] + [
        {**_row(100 + i, -1.0), "market_regime": "RANGING"} for i in range(12)
    ]
    source.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    report = build_walk_forward_report(source, train_size=5, test_size=3, step=3, min_test_samples=3)
    assert {row["market_regime"] for row in report["stats"]} == {"TRENDING", "RANGING"}
    assert all(row["walk_forward_evidence_available"] for row in report["stats"])
    assert report["paper_only"] is True
    assert report["orders_submitted"] is False
    assert report["execution_authorized"] is False
