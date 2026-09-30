# Path: tests/test_hot_path_outcome_study.py
import json

from PC_ENGINE.research.hot_path_outcome_study import (
    load_hot_path_outcomes,
    run_hot_path_outcome_study,
    write_hot_path_outcome_study,
)


def _row(index: int, net: float) -> dict:
    return {
        "status": "COMPLETED",
        "paper_only": True,
        "orders_submitted": False,
        "symbol": "BTC/USDT",
        "leader": "binance",
        "follower": "coinbase",
        "direction": "UP",
        "outcome_local_ts_ms": 1000 + index * 100,
        "realized_net_bps": net,
        "expected_net_bps": 2.0,
    }


def test_oos_study_uses_chronological_holdout_not_training_results():
    rows = [_row(i, -5.0) for i in range(7)] + [_row(i + 7, 3.0) for i in range(3)]
    report = run_hot_path_outcome_study(
        rows,
        min_samples=10,
        min_test_samples=3,
        train_fraction=0.7,
        min_test_net_bps=0.0,
    )
    relationship = report["relationships_detail"][0]
    assert relationship["train"]["mean_net_bps"] == -5.0
    assert relationship["test"]["mean_net_bps"] == 3.0
    assert relationship["eligible_for_oos_review"] is True
    assert report["real_authorization_changed"] is False


def test_negative_oos_edge_is_not_eligible():
    rows = [_row(i, 4.0) for i in range(7)] + [_row(i + 7, -2.0) for i in range(3)]
    report = run_hot_path_outcome_study(rows, min_samples=10, min_test_samples=3)
    assert report["eligible_relationships"] == 0
    assert report["relationships_detail"][0]["status"] == "OOS_EDGE_NOT_CONFIRMED"


def test_insufficient_samples_never_become_eligible():
    report = run_hot_path_outcome_study([_row(0, 10.0), _row(1, 10.0)], min_samples=10, min_test_samples=2)
    assert report["eligible_relationships"] == 0
    assert report["relationships_detail"][0]["status"] == "INSUFFICIENT_EVIDENCE"


def test_loader_counts_malformed_json_and_limits_records(tmp_path):
    path = tmp_path / "outcomes.jsonl"
    path.write_text(
        json.dumps(_row(1, 1.0)) + "\nnot-json\n" + json.dumps(_row(2, 2.0)) + "\n",
        encoding="utf-8",
    )
    rows, invalid = load_hot_path_outcomes(path, limit=1)
    assert len(rows) == 1
    assert invalid == 1
    assert rows[0]["realized_net_bps"] == 2.0


def test_report_is_written_atomically_as_json(tmp_path):
    path = tmp_path / "reports" / "hot_path_outcome_study.json"
    report = run_hot_path_outcome_study([])
    write_hot_path_outcome_study(report, path)
    assert json.loads(path.read_text(encoding="utf-8"))["orders_submitted"] is False
    assert not path.with_suffix(".json.tmp").exists()
