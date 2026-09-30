# Path: tests/test_hot_path_persistence.py
import json

from PC_ENGINE.radar.hot_path_persistence import append_paper_outcomes


def _row(value: int = 1):
    return {
        "schema_version": 1,
        "status": "COMPLETED",
        "paper_only": True,
        "orders_submitted": False,
        "symbol": "BTC/USDT",
        "realized_net_bps": float(value),
    }


def test_append_repairs_only_a_torn_final_jsonl_record(tmp_path):
    path = tmp_path / "hot_path_outcomes.jsonl"
    first = _row(1)
    path.write_text(json.dumps(first) + "\n" + '{"torn":', encoding="utf-8")

    assert append_paper_outcomes(path, [_row(2)]) == 1
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0]) == first
    assert json.loads(lines[1]) == _row(2)


def test_append_filters_anything_that_is_not_completed_paper_evidence(tmp_path):
    path = tmp_path / "hot_path_outcomes.jsonl"

    written = append_paper_outcomes(path, [
        _row(),
        {**_row(99), "orders_submitted": True},
        {**_row(88), "paper_only": False},
        {**_row(77), "status": "PENDING"},
    ])

    assert written == 1
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert rows == [_row()]


def test_append_empty_or_unsafe_batch_does_not_create_file(tmp_path):
    path = tmp_path / "nested" / "outcomes.jsonl"
    assert append_paper_outcomes(path, [{**_row(), "orders_submitted": True}]) == 0
    assert not path.exists()
