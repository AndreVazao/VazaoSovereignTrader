import json
import time

from PC_ENGINE.radar.hot_path_relationship_oos import (
    build_relationship_oos_report,
    write_relationship_oos_report,
)


def _row(i, net, **extra):
    return {
        "status": "COMPLETED",
        "paper_only": True,
        "orders_submitted": False,
        "outcome_id": f"paper-{i}",
        "symbol": "BTC/USDT",
        "leader": "binance",
        "follower": "coinbase",
        "direction": "UP",
        "horizon_ms": 500,
        "expected_net_bps": 1.0,
        "realized_net_bps": net,
        "outcome_local_ts_ms": 1_000 + i * 1_000,
        **extra,
    }


def test_relationship_oos_splits_each_relationship_chronologically(tmp_path):
    path = tmp_path / "outcomes.jsonl"
    rows = [_row(i, -2.0) for i in range(70)] + [_row(i, 3.0) for i in range(70, 100)]
    rows += [
        {**_row(i, 2.0), "symbol": "ETH/USDT", "outcome_id": f"eth-{i}"}
        for i in range(10, 20)
    ]
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

    report = build_relationship_oos_report(
        path, min_samples=100, min_test_samples=20, train_fraction=0.7, now_ms=200_000,
    )

    assert report["relationships"] == 2
    btc = next(row for row in report["relationship_details"] if row["symbol"] == "BTC/USDT")
    assert btc["train_samples"] == 70
    assert btc["test_samples"] == 30
    assert btc["train_end_ms"] < btc["test_start_ms"]
    assert btc["train_mean_net_bps"] == -2.0
    assert btc["oos_mean_net_bps"] == 3.0
    assert btc["oos_ci95_method"] == "moving_block_bootstrap"
    assert btc["oos_bootstrap_replicates"] >= 500
    assert btc["oos_confidence_interval_available"] is True
    assert btc["oos_edge_supported"] is True
    assert report["execution_authorized"] is False


def test_relationship_oos_excludes_corrupt_nonpaper_invalid_and_future_rows(tmp_path):
    path = tmp_path / "outcomes.jsonl"
    now = time.time_ns() // 1_000_000
    valid = [_row(i, 1.0, outcome_local_ts_ms=now - (10 - i) * 1000) for i in range(8)]
    invalid = {**_row(90, 99.0), "realized_net_bps": "NaN"}
    future = {**_row(91, 99.0), "outcome_local_ts_ms": now + 10_000}
    nonpaper = {**_row(92, 99.0), "orders_submitted": True}
    path.write_bytes(
        ("\n".join(json.dumps(row) for row in valid) + "\n").encode()
        + b"\xff\xfe\n{bad json\n"
        + (json.dumps(invalid) + "\n" + json.dumps(future) + "\n" + json.dumps(nonpaper) + "\n").encode()
    )

    report = build_relationship_oos_report(path, min_samples=5, min_test_samples=2)

    assert report["valid_unique_outcomes"] == 8
    assert report["malformed_lines_ignored"] == 2
    assert report["invalid_outcomes_ignored"] == 2
    assert report["non_paper_records_ignored"] == 1
    assert report["execution_authorized"] is False


def test_invalid_first_row_does_not_suppress_later_valid_duplicate(tmp_path):
    path = tmp_path / "outcomes.jsonl"
    invalid = {**_row(1, 100.0), "outcome_id": "same"}
    invalid["realized_net_bps"] = "not-a-number"
    valid = {**_row(2, 2.0), "outcome_id": "same"}
    path.write_text(json.dumps(invalid) + "\n" + json.dumps(valid) + "\n", encoding="utf-8")

    report = build_relationship_oos_report(path, min_samples=2, min_test_samples=1, now_ms=100_000)

    assert report["valid_unique_outcomes"] == 1
    assert report["invalid_outcomes_ignored"] == 1
    assert report["duplicate_outcomes_ignored"] == 0
    assert report["relationship_details"][0]["oos_mean_net_bps"] is None
    assert report["execution_authorized"] is False


def test_relationship_oos_requires_sample_threshold_and_writes_atomically(tmp_path):
    source = tmp_path / "outcomes.jsonl"
    rows = [_row(i, 2.0) for i in range(4)]
    source.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    target = tmp_path / "reports" / "relationship-oos.json"

    report = write_relationship_oos_report(
        source, target, min_samples=10, min_test_samples=2, now_ms=100_000,
    )

    saved = json.loads(target.read_text(encoding="utf-8"))
    assert saved["relationships"] == 1
    assert saved["relationship_details"][0]["sample_sufficiency"] == "INSUFFICIENT"
    assert saved["eligible_relationships_for_paper_review"] == 0
    assert saved["paper_only"] is True
    assert saved["orders_submitted"] is False
    assert saved["execution_authorized"] is False


def test_relationship_oos_never_splits_equal_timestamps_across_train_and_test(tmp_path):
    path = tmp_path / "outcomes.jsonl"
    rows = [_row(i, 1.0) for i in range(10)]
    rows[7]["outcome_local_ts_ms"] = rows[6]["outcome_local_ts_ms"]
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

    report = build_relationship_oos_report(
        path, min_samples=10, min_test_samples=2, train_fraction=0.7, now_ms=100_000,
    )
    relationship = report["relationship_details"][0]
    assert relationship["train_samples"] == 8
    assert relationship["test_samples"] == 2
    assert relationship["train_end_ms"] < relationship["test_start_ms"]
