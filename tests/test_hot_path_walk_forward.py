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
        "outcome_local_ts_ms": 1_000 + i * 1_000,
        "outcome_id": f"outcome-{i}",
    }


def test_walk_forward_uses_future_windows_as_oos_only(tmp_path):
    source = tmp_path / "outcomes.jsonl"
    rows = [_row(i, 1.0) for i in range(6)] + [_row(i, -1.0) for i in range(6, 12)]
    source.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

    report = build_walk_forward_report(source, train_size=4, test_size=2, min_test_samples=2)

    assert report["paper_only"] is True
    assert report["orders_submitted"] is False
    assert report["execution_authorized"] is False
    assert report["fold_count"] == 4
    assert report["folds"][0]["train_end_ms"] < report["folds"][0]["test_start_ms"]
    assert report["folds"][0]["train_mean_realized_net_bps"] == 1.0
    assert report["folds"][0]["test_mean_realized_net_bps"] == 1.0
    assert report["folds"][-1]["test_mean_realized_net_bps"] == -1.0


def test_walk_forward_excludes_unusable_and_non_paper_rows(tmp_path):
    source = tmp_path / "outcomes.jsonl"
    rows = [_row(i, 1.0) for i in range(8)]
    rows.append({**_row(99, 50.0), "orders_submitted": True})
    rows.append({**_row(100, 50.0), "outcome_local_ts_ms": 0})
    rows.append({**_row(101, 50.0), "realized_net_bps": "nan"})
    source.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

    report = build_walk_forward_report(source, train_size=4, test_size=2, min_test_samples=2)

    assert report["raw_completed_paper_records"] == 10
    assert report["timestamped_valid_records"] == 8
    assert report["fold_count"] == 2
    assert report["folds"][0]["test_start_ms"] == 5_000


def test_walk_forward_deduplicates_outcomes_and_keeps_timestamp_order(tmp_path):
    source = tmp_path / "outcomes.jsonl"
    rows = [_row(i, float(i)) for i in [3, 1, 2, 4, 5, 6]]
    rows.append({**rows[0], "realized_net_bps": 99.0})
    source.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

    report = build_walk_forward_report(source, train_size=2, test_size=2, min_test_samples=2)

    assert report["timestamped_valid_records"] == 6
    assert report["folds"][0]["train_start_ms"] < report["folds"][0]["train_end_ms"]
    assert report["folds"][0]["test_start_ms"] < report["folds"][0]["test_end_ms"]
    assert report["folds"][0]["test_start_ms"] > report["folds"][0]["train_end_ms"]
    assert report["folds"][0]["test_mean_realized_net_bps"] == 3.5
