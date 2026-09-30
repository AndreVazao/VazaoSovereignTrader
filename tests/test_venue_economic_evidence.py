from __future__ import annotations

import json

from PC_ENGINE.diagnostics.venue_economic_evidence import build_venue_economic_evidence


def _outcome(i: int, *, follower: str = "coinbase", net: float = 2.0, ts: int | None = None):
    return {
        "status": "COMPLETED",
        "paper_only": True,
        "orders_submitted": False,
        "outcome_id": f"o-{i}",
        "symbol": "BTC/USDT",
        "leader": "binance",
        "follower": follower,
        "direction": "UP",
        "horizon_ms": 500,
        "realized_net_bps": net,
        "fees_bps": 2.0,
        "slippage_bps": 1.0,
        "latency_penalty_bps": 0.5,
        "outcome_local_ts_ms": ts if ts is not None else 1_000 + i,
    }


def test_venue_economic_evidence_is_paper_only_and_separate_from_health(tmp_path):
    path = tmp_path / "outcomes.jsonl"
    rows = [_outcome(i, net=-1.0 if i < 25 else 3.0) for i in range(40)]
    rows.append(_outcome(100, follower="not-configured", net=100.0))
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

    report = build_venue_economic_evidence(
        {"radar": {"websocket_exchanges": ["coinbase"], "polling_exchanges": ["binance"]}},
        path,
        now_ms=10_000,
        min_samples=20,
        min_oos_samples=8,
    )

    by_venue = {row["venue"]: row for row in report["venues"]}
    assert set(by_venue) == {"coinbase", "binance"}
    assert by_venue["coinbase"]["paper_outcome_samples"] == 40
    assert by_venue["coinbase"]["status"] == "POSITIVE_OOS_CANDIDATE"
    assert by_venue["coinbase"]["oos_confidence_interval_available"] is True
    assert by_venue["coinbase"]["oos_ci95_lower_bps"] > 0
    assert by_venue["coinbase"]["oos_bootstrap_replicates"] >= 500
    assert by_venue["coinbase"]["mean_recorded_fees_bps"] == 2.0
    assert by_venue["coinbase"]["spread_bps"] is None
    assert by_venue["coinbase"]["spread_status"] == "UNAVAILABLE_NO_BID_ASK_EVIDENCE"
    assert by_venue["binance"]["status"] == "INSUFFICIENT_DATA"
    assert report["paper_only"] is True
    assert report["orders_submitted"] is False
    assert report["execution_authorized"] is False


def test_economic_evidence_rejects_future_and_non_paper_rows_and_tolerates_corruption(tmp_path):
    path = tmp_path / "outcomes.jsonl"
    rows = [
        _outcome(1, ts=900),
        _outcome(2, ts=1_001),
        {**_outcome(3), "paper_only": False},
    ]
    path.write_bytes(
        b"\xff\xfe\n{bad json\n"
        + ("\n".join(json.dumps(row) for row in rows) + "\n").encode("utf-8")
    )

    report = build_venue_economic_evidence(
        {"radar": {"websocket_exchanges": ["coinbase"]}},
        path,
        now_ms=1_000,
        min_samples=1,
        min_oos_samples=1,
    )
    venue = report["venues"][0]
    assert venue["paper_outcome_samples"] == 1
    assert venue["status"] == "INSUFFICIENT_OOS_FOR_CI"
    assert venue["oos_confidence_interval_available"] is False
    assert report["integrity"]["malformed_lines_ignored"] == 2
    assert report["integrity"]["non_paper_records_ignored"] == 1
    assert report["execution_authorized"] is False


def test_economic_evidence_marks_non_positive_holdout_for_review(tmp_path):
    path = tmp_path / "outcomes.jsonl"
    path.write_text("\n".join(json.dumps(_outcome(i, net=-0.5)) for i in range(40)) + "\n", encoding="utf-8")
    report = build_venue_economic_evidence(
        {"radar": {"websocket_exchanges": ["coinbase"]}},
        path,
        now_ms=10_000,
        min_samples=20,
        min_oos_samples=8,
    )
    assert report["venues"][0]["status"] == "NON_POSITIVE_OOS"
    assert report["venues"][0]["oos_mean_realized_net_bps"] == -0.5



def test_economic_evidence_marks_mixed_holdout_as_uncertain(tmp_path):
    path = tmp_path / "outcomes.jsonl"
    rows = [_outcome(i, net=(2.0 if i % 2 else -2.0)) for i in range(50)]
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    report = build_venue_economic_evidence(
        {"radar": {"websocket_exchanges": ["coinbase"]}},
        path,
        now_ms=10_000,
        min_samples=30,
        min_oos_samples=8,
    )
    venue = report["venues"][0]
    assert venue["status"] == "UNCERTAIN_OOS"
    assert venue["oos_confidence_interval_available"] is True
    assert venue["oos_ci95_lower_bps"] <= 0 <= venue["oos_ci95_upper_bps"]
    assert venue["oos_edge_supported"] is False



def test_spread_uses_only_fresh_valid_public_top_of_book_observations(tmp_path):
    outcomes = tmp_path / "outcomes.jsonl"
    outcomes.write_text(
        "\n".join(json.dumps(_outcome(i, net=1.0)) for i in range(40)) + "\n",
        encoding="utf-8",
    )
    ticker_path = tmp_path / "ticker.jsonl"
    base = {
        "venue": "coinbase",
        "symbol": "BTC/USDT",
        "event_type": "ticker",
        "local_receive_wall_ns": 10_000_000_000,
        "observation_type": "PUBLIC_TOP_OF_BOOK",
        "paper_only": True,
        "orders_submitted": False,
        "execution_authorized": False,
    }
    rows = [
        {**base, "event_id": "t1", "bid": 100.0, "ask": 100.2},
        {**base, "event_id": "t2", "bid": 100.1, "ask": 100.3},
        {**base, "event_id": "crossed", "bid": 101.0, "ask": 100.0},
        {**base, "event_id": "nonpaper", "bid": 100.0, "ask": 100.1, "orders_submitted": True},
    ]
    ticker_path.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n{bad json\n",
        encoding="utf-8",
    )

    report = build_venue_economic_evidence(
        {"radar": {"websocket_exchanges": ["coinbase"]}},
        outcomes,
        now_ms=10_000,
        min_samples=20,
        min_oos_samples=8,
        top_of_book_path=ticker_path,
        top_of_book_min_samples=2,
        top_of_book_max_age_ms=5_000,
    )
    venue = report["venues"][0]
    assert venue["spread_status"] == "AVAILABLE"
    assert venue["spread_samples"] == 2
    assert 19.0 < venue["spread_bps"] < 21.0
    assert report["integrity"]["ticker_invalid_ignored"] == 1
    assert report["integrity"]["ticker_non_paper_ignored"] == 1
    assert report["integrity"]["ticker_malformed_ignored"] == 1
    assert report["execution_authorized"] is False


def test_top_of_book_reports_freshness_and_coverage_per_venue_symbol(tmp_path):
    outcomes = tmp_path / "outcomes.jsonl"
    outcomes.write_text(
        "\n".join(json.dumps(_outcome(i, net=1.0)) for i in range(20)) + "\n",
        encoding="utf-8",
    )
    ticker_path = tmp_path / "ticker.jsonl"
    base = {
        "venue": "coinbase",
        "event_type": "ticker",
        "observation_type": "PUBLIC_TOP_OF_BOOK",
        "paper_only": True,
        "orders_submitted": False,
        "execution_authorized": False,
    }
    rows = [
        {**base, "event_id": "btc-1", "symbol": "BTC/USDT", "bid": 100.0, "ask": 100.2, "local_receive_wall_ns": 9_500_000_000},
        {**base, "event_id": "btc-2", "symbol": "BTC/USDT", "bid": 100.1, "ask": 100.3, "local_receive_wall_ns": 9_000_000_000},
        {**base, "event_id": "eth-1", "symbol": "ETH/USDT", "bid": 200.0, "ask": 200.4, "local_receive_wall_ns": 9_900_000_000},
        {**base, "event_id": "stale", "symbol": "ETH/USDT", "bid": 200.0, "ask": 200.4, "local_receive_wall_ns": 1_000_000_000},
    ]
    ticker_path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

    report = build_venue_economic_evidence(
        {"radar": {"websocket_exchanges": ["coinbase"]}},
        outcomes,
        now_ms=10_000,
        min_samples=10,
        min_oos_samples=8,
        top_of_book_path=ticker_path,
        top_of_book_max_age_ms=2_000,
        top_of_book_min_samples=1,
    )

    venue = report["venues"][0]
    coverage = {row["symbol"]: row for row in report["top_of_book_coverage"]}
    assert venue["top_of_book_valid_observations"] == 3
    assert venue["top_of_book_last_observation_age_ms"] == 100
    assert venue["top_of_book_symbol_coverage"][0]["symbol"] == "BTC/USDT"
    assert coverage["BTC/USDT"]["valid_observations"] == 2
    assert coverage["BTC/USDT"]["age_p95_ms"] == 1000
    assert coverage["ETH/USDT"]["valid_observations"] == 1
    assert report["integrity"]["ticker_stale_ignored"] == 1
