# Path: tests/test_hot_path_calibration.py
import json

from PC_ENGINE.radar.hot_path_calibration import build_hot_path_calibration, write_hot_path_calibration


def _outcome(realized_net: float, expected_net: float = 3.0):
    return {
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
    assert report["stats"][0]["eligible_for_paper_review"] is True


def test_calibration_requires_minimum_samples_and_positive_lower_bound(tmp_path):
    source = tmp_path / "hot_path_outcomes.jsonl"
    rows = [_outcome(1.0) for _ in range(3)] + [_outcome(-5.0) for _ in range(10)]
    source.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

    report = build_hot_path_calibration(source, min_samples=5)

    assert report["stats"][0]["samples"] == 13
    assert report["stats"][0]["eligible_for_paper_review"] is False
    assert report["execution_authorized"] is False


def test_calibration_ignores_non_paper_or_malformed_rows_and_writes_atomically(tmp_path):
    source = tmp_path / "hot_path_outcomes.jsonl"
    source.write_text(
        json.dumps(_outcome(2.0)) + "\n"
        + json.dumps({**_outcome(99.0), "orders_submitted": True}) + "\n"
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
        {**_outcome(2.0 + i * 0.01), "market_regime": "TRENDING"}
        for i in range(4)
    ] + [
        {**_outcome(-2.0 - i * 0.01), "market_regime": "RANGING"}
        for i in range(4)
    ] + [
        _outcome(1.0)
    ]
    source.write_text("\\n".join(json.dumps(row) for row in rows) + "\\n", encoding="utf-8")

    report = build_hot_path_calibration(source, min_samples=2)

    by_regime = {row["market_regime"]: row for row in report["stats"]}
    assert set(by_regime) == {"TRENDING", "RANGING", "UNCLASSIFIED"}
    assert by_regime["TRENDING"]["samples"] == 4
    assert by_regime["RANGING"]["samples"] == 4
    assert by_regime["UNCLASSIFIED"]["samples"] == 1
    assert by_regime["TRENDING"]["mean_realized_net_bps"] > 0
    assert by_regime["RANGING"]["mean_realized_net_bps"] < 0
    assert report["execution_authorized"] is False
