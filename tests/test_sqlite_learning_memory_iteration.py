from __future__ import annotations

import pytest

from PC_ENGINE.learning.sqlite_memory import SQLiteLearningMemory


def _put(memory, key: str, *, status: str = "testing", ttl_ms: int | None = None):
    return memory.put(
        key=key,
        value={"key": key},
        department="research",
        provenance="bounded-iterator-test",
        status=status,
        ttl_ms=ttl_ms,
    )


def test_iter_records_reads_all_rows_in_small_keyset_pages(tmp_path):
    with SQLiteLearningMemory(tmp_path / "learning.sqlite3") as memory:
        expected = tuple(_put(memory, f"record.{index:03d}") for index in range(17))

        actual = tuple(memory.iter_records(batch_size=3))

        assert actual == expected
        assert [record.key for record in actual] == sorted(record.key for record in expected)


def test_iter_records_applies_status_after_expiry_classification(tmp_path):
    now = [1_800_000_000_000_000_000]
    with SQLiteLearningMemory(tmp_path / "learning.sqlite3", clock_ns=lambda: now[0]) as memory:
        _put(memory, "a.expired", status="supported", ttl_ms=1)
        _put(memory, "b.current", status="supported")
        _put(memory, "c.testing", status="testing")
        now[0] += 2_000_000

        stale = tuple(memory.iter_records(status="stale", batch_size=1))
        supported = tuple(memory.iter_records(status="supported", batch_size=1))

        assert [record.key for record in stale] == ["a.expired"]
        assert [record.key for record in supported] == ["b.current"]


@pytest.mark.parametrize("batch_size", [0, -1, True, 1.5, "10"])
def test_iter_records_rejects_invalid_batch_sizes(tmp_path, batch_size):
    with SQLiteLearningMemory(tmp_path / "learning.sqlite3") as memory:
        with pytest.raises(ValueError, match="batch_size"):
            tuple(memory.iter_records(batch_size=batch_size))


def test_iter_records_rejects_unknown_status(tmp_path):
    with SQLiteLearningMemory(tmp_path / "learning.sqlite3") as memory:
        with pytest.raises(ValueError, match="status"):
            tuple(memory.iter_records(status="approved-by-magic"))
