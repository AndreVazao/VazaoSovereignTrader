import json

from PC_ENGINE.radar.hot_path_calibration import build_hot_path_calibration, write_hot_path_calibration


def _outcome(realized_net: float, expected_net: float = 3.0):
    return {
        "status": "COMPLETED",
        "paper_only": True,
        "orders_submitted": False,
        "symbol": "BTC/USDT",
        "leader": "binance",
        "follower": "coinbase",
        "direction": "UP",
        "horizon_ms": 500,
        "expected_net_bps": expected_net,
        "realized_net_bps": realized_net,
        "realized_response_bps": realized_net + 6.0,
    }


def test_calibration_is_diagnostic_and_never_authorizes_execution(tmp_path):
    source = tmp_path / "hot_path_outcomes.jsonl"
    source.write_text("\n".join(json.dumps(_outcome(2.0 + i * 0.01)) for i in range(10)) + "\n", encoding="utf-8")
    report = build_hot_path_calibration(source, min_samples=5)
    assert report["paper_only"] is True
    assert report["orders_submitted"] is False
    assert report["execution_authorized"] is False
    assert report["outcome_samples"] == 10
    assert report["invalid_outcomes_ignored"] == 0
    assert report["stats"][0]["eligible_for_paper_review"] is True


def test_calibration_requires_minimum_samples_and_positive_lower_bound(tmp_path):
    source = tmp_path / "hot_path_outcomes.jsonl"
    rows = [_outcome(1.0) for _ in range(3)] + [_outcome(-5.0) for _ in range(10)]
    source.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    report = build_hot_path_calibration(source, min_samples=5)
    assert report["stats"][0]["samples"] == 2
    assert report["duplicate_outcomes_ignored"] == 11
    assert report["stats"][0]["eligible_for_paper_review"] is False
    assert report["execution_authorized"] is False


def test_calibration_ignores_non_paper_incomplete_or_malformed_rows_and_writes_atomically(tmp_path):
    source = tmp_path / "hot_path_outcomes.jsonl"
    source.write_text(
        json.dumps(_outcome(2.0)) + "\n"
        + json.dumps({**_outcome(99.0), "orders_submitted": True}) + "\n"
        + json.dumps({**_outcome(88.0), "status": "PENDING"}) + "\n"
        + "{bad json\n",
        encoding="utf-8",
    )
    destination = tmp_path / "report.json"
    report = write_hot_path_calibration(source, destination, min_samples=2)
    assert destination.exists()
    assert json.loads(destination.read_text(encoding="utf-8"))["outcome_samples"] == 1
    assert report["outcome_samples"] == 1
    assert report["stats"][0]["eligible_for_paper_review"] is False


def test_calibration_keeps_market_regimes_separate_and_marks_missing_regime(tmp_path):
    source = tmp_path / "hot_path_outcomes.jsonl"
    rows = [
        {**_outcome(2.0 + i * 0.01), "market_regime": "TRENDING"} for i in range(4)
    ] + [
        {**_outcome(-2.0 - i * 0.01), "market_regime": "RANGING"} for i in range(4)
    ] + [_outcome(1.0)]
    source.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    report = build_hot_path_calibration(source, min_samples=2)
    by_regime = {row["market_regime"]: row for row in report["stats"]}
    assert set(by_regime) == {"TRENDING", "RANGING", "UNCLASSIFIED"}
    assert by_regime["TRENDING"]["samples"] == 4
    assert by_regime["RANGING"]["samples"] == 4
    assert by_regime["UNCLASSIFIED"]["samples"] == 1
    assert by_regime["TRENDING"]["mean_realized_net_bps"] > 0
    assert by_regime["RANGING"]["mean_realized_net_bps"] < 0
    assert report["execution_authorized"] is False


def test_calibration_deduplicates_identical_legacy_rows(tmp_path):
    source = tmp_path / "hot_path_outcomes.jsonl"
    row = _outcome(2.0)
    source.write_text("\n".join(json.dumps(value) for value in [row, row, row]) + "\n", encoding="utf-8")
    report = build_hot_path_calibration(source, min_samples=2)
    assert report["outcome_samples"] == 1
    assert report["duplicate_outcomes_ignored"] == 2
    assert report["stats"][0]["samples"] == 1
    assert report["stats"][0]["eligible_for_paper_review"] is False
    assert report["execution_authorized"] is False


def test_calibration_uses_stable_outcome_id_to_deduplicate(tmp_path):
    source = tmp_path / "hot_path_outcomes.jsonl"
    first = {**_outcome(2.0), "outcome_id": "outcome-123"}
    duplicate_with_conflicting_values = {**_outcome(99.0), "outcome_id": "outcome-123"}
    source.write_text(json.dumps(first) + "\n" + json.dumps(duplicate_with_conflicting_values) + "\n", encoding="utf-8")
    report = build_hot_path_calibration(source, min_samples=2)
    assert report["outcome_samples"] == 1
    assert report["duplicate_outcomes_ignored"] == 1
    assert report["stats"][0]["mean_realized_net_bps"] == 2.0


def test_calibration_does_not_count_completed_but_invalid_rows_as_samples(tmp_path):
    source = tmp_path / "hot_path_outcomes.jsonl"
    valid = _outcome(2.0)
    missing_metric = {**_outcome(100.0)}
    del missing_metric["expected_net_bps"]
    invalid_number = {**_outcome(200.0), "realized_net_bps": float("nan")}
    source.write_text("\n".join(json.dumps(row) for row in [valid, missing_metric, invalid_number]) + "\n", encoding="utf-8")
    report = build_hot_path_calibration(source, min_samples=2)
    assert report["outcome_records_loaded"] == 3
    assert report["unique_completed_paper_records"] == 3
    assert report["outcome_samples"] == 1
    assert report["invalid_outcomes_ignored"] == 2
    assert report["stats"][0]["samples"] == 1
    assert report["execution_authorized"] is False


def test_calibration_penalizes_positive_serial_dependence(tmp_path):
    source = tmp_path / "hot_path_outcomes.jsonl"
    rows = []
    for i in range(12):
        rows.append({**_outcome(2.0 + (i // 4) * 0.1), "outcome_local_ts_ms": 1_000 + i * 500})
    source.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    report = build_hot_path_calibration(source, min_samples=5)
    stat = report["stats"][0]
    assert stat["temporal_dependence_assessment"] == "AVAILABLE"
    assert stat["timestamped_samples"] == 12
    assert stat["effective_samples"] < stat["samples"]
    assert stat["ci95_sample_basis"] == "effective_samples"
    assert stat["lag1_autocorrelation"] > 0
    assert stat["ci95_method"] == "moving_block_bootstrap"
    assert stat["bootstrap_replicates"] == 1000
    assert stat["bootstrap_block_length"] >= 2
    assert stat["net_ci95_lower_bps"] <= stat["mean_realized_net_bps"] <= stat["net_ci95_upper_bps"]
    assert report["execution_authorized"] is False


def test_calibration_bootstrap_is_deterministic_for_same_evidence(tmp_path):
    source = tmp_path / "hot_path_outcomes.jsonl"
    rows = [
        {**_outcome(1.0 + (i % 5) * 0.25), "outcome_local_ts_ms": 10_000 + i * 500}
        for i in range(20)
    ]
    source.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    first = build_hot_path_calibration(source, min_samples=5)
    second = build_hot_path_calibration(source, min_samples=5)
    assert first["stats"][0]["net_ci95_lower_bps"] == second["stats"][0]["net_ci95_lower_bps"]
    assert first["stats"][0]["net_ci95_upper_bps"] == second["stats"][0]["net_ci95_upper_bps"]


def test_calibration_keeps_legacy_rows_usable_without_fake_temporal_data(tmp_path):
    source = tmp_path / "hot_path_outcomes.jsonl"
    rows = [{**_outcome(2.0 + i * 0.01), "outcome_id": f"legacy-{i}"} for i in range(6)]
    source.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    report = build_hot_path_calibration(source, min_samples=5)
    stat = report["stats"][0]
    assert stat["temporal_dependence_assessment"] == "UNAVAILABLE"
    assert stat["timestamped_samples"] == 0
    assert stat["effective_samples"] == 6
    assert stat["ci95_sample_basis"] == "samples"
    assert stat["ci95_method"] == "sample_normal"
    assert stat["bootstrap_replicates"] == 0
    assert stat["eligible_for_paper_review"] is True


def test_calibration_skips_invalid_utf8_and_continues_reading(tmp_path):
    source = tmp_path / "outcomes.jsonl"
    valid_first = json.dumps(_outcome(2.0)).encode("utf-8") + b"\n"
    corrupt = b"\xff\xfe\n"
    malformed = b"{bad json\n"
    valid_last = json.dumps(_outcome(4.0)).encode("utf-8") + b"\n"
    source.write_bytes(valid_first + corrupt + malformed + valid_last)
    report = build_hot_path_calibration(source, min_samples=2)
    assert report["outcome_records_loaded"] == 2
    assert report["outcome_samples"] == 1
    assert report["duplicate_outcomes_ignored"] == 1


def test_calibration_excludes_future_timestamps_from_temporal_evidence(tmp_path):
    source = tmp_path / "outcomes.jsonl"
    now_ms = __import__("time").time_ns() // 1_000_000
    rows = [
        {**_outcome(1.0 + i / 10), "outcome_id": f"future-check-{i}",
         "outcome_local_ts_ms": now_ms + 10_000 if i == 11 else now_ms - (12 - i) * 1000}
        for i in range(12)
    ]
    source.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    report = build_hot_path_calibration(source, min_samples=5)
    assert report["outcome_samples"] == 12
    assert report["stats"][0]["timestamped_samples"] == 11
