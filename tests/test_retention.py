from __future__ import annotations

import json
import time

from PC_ENGINE.core.retention import retain_jsonl


def test_retain_jsonl_keeps_recent_bounded_rows(tmp_path):
    path = tmp_path / "evidence.jsonl"
    now = int(time.time() * 1000)
    rows = [
        {"timestamp_ms": now - 3_000, "value": 1},
        {"timestamp_ms": now - 2_000, "value": 2},
        {"timestamp_ms": now - 1_000, "value": 3},
        {"timestamp_ms": now, "value": 4},
    ]
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    kept = retain_jsonl(path, max_rows=2, max_age_ms=10_000)

    assert kept == 2
    result = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert [row["value"] for row in result] == [3, 4]


def test_retain_jsonl_discards_stale_rows(tmp_path):
    path = tmp_path / "evidence.jsonl"
    now = int(time.time() * 1000)
    rows = [
        {"timestamp_ms": now - 20_000, "value": "old"},
        {"timestamp_ms": now - 100, "value": "new"},
    ]
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    retain_jsonl(path, max_rows=100, max_age_ms=1_000)

    result = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert [row["value"] for row in result] == ["new"]
