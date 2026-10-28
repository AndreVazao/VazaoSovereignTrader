from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import threading

import pytest

from PC_ENGINE.learning.shared_memory import VersionConflict
from PC_ENGINE.learning.sqlite_memory import SQLiteLearningMemory


def test_records_survive_close_and_reopen(tmp_path):
    database = tmp_path / "learning.sqlite3"
    with SQLiteLearningMemory(database) as first:
        saved = first.put(
            key="temporal.btc-usdt.binance-bingx",
            value={"net_edge_bps": 2.4, "sample_count": 120},
            department="analysis",
            provenance="replay:case-007",
            status="testing",
            confidence=0.72,
        )

    with SQLiteLearningMemory(database) as second:
        restored = second.get(saved.key)
        assert restored == saved
        assert restored.value == {"net_edge_bps": 2.4, "sample_count": 120}
        assert second.list_records(status="testing") == (saved,)
        events = second.list_events(key=saved.key)
        assert len(events) == 1
        assert events[0].version == 1
        assert events[0].event_type == "put"


def test_version_conflict_is_atomic_and_durable(tmp_path):
    database = tmp_path / "learning.sqlite3"
    with SQLiteLearningMemory(database) as memory:
        first = memory.put(
            key="hypothesis.alpha",
            value={"result": "candidate"},
            department="research",
            provenance="synthetic",
        )
        second = memory.put(
            key=first.key,
            value={"result": "updated"},
            department="analysis",
            provenance="replay",
            expected_version=first.version,
        )
        with pytest.raises(VersionConflict):
            memory.put(
                key=first.key,
                value={"result": "stale overwrite"},
                department="research",
                provenance="old-worker",
                expected_version=first.version,
            )
        assert memory.get(first.key) == second
        assert [event.version for event in memory.list_events(key=first.key)] == [1, 2]


def test_expired_evidence_is_stale_after_reopening(tmp_path):
    now = [1_800_000_000_000_000_000]
    database = tmp_path / "learning.sqlite3"
    with SQLiteLearningMemory(database, clock_ns=lambda: now[0]) as memory:
        record = memory.put(
            key="venue.edge",
            value={"edge_bps": 1.1},
            department="analysis",
            provenance="synthetic",
            status="supported",
            confidence=0.9,
            ttl_ms=10,
        )

    now[0] += 11_000_000
    with SQLiteLearningMemory(database, clock_ns=lambda: now[0]) as reopened:
        assert reopened.get(record.key).status == "stale"
        assert reopened.list_records(status="stale")[0].key == record.key
        assert reopened.list_records(status="supported") == ()


def test_invalid_values_and_metadata_fail_closed(tmp_path):
    with SQLiteLearningMemory(tmp_path / "learning.sqlite3") as memory:
        with pytest.raises(ValueError, match="JSON-serializable"):
            memory.put(
                key="not-json",
                value={"bad": object()},
                department="research",
                provenance="test",
            )
        with pytest.raises(ValueError, match="JSON-serializable"):
            memory.put(
                key="not-finite",
                value={"bad": float("nan")},
                department="research",
                provenance="test",
            )
        with pytest.raises(ValueError, match="confidence"):
            memory.put(
                key="bad-confidence",
                value={"ok": True},
                department="analysis",
                provenance="test",
                confidence=float("inf"),
            )
        with pytest.raises(ValueError, match="ttl_ms"):
            memory.put(
                key="bad-ttl",
                value=1,
                department="research",
                provenance="test",
                ttl_ms=0,
            )

        for invalid_version in (True, False, -1, 1.5, "1"):
            with pytest.raises(ValueError, match="expected_version"):
                memory.put(
                    key="bad-version",
                    value={"ok": True},
                    department="research",
                    provenance="test",
                    expected_version=invalid_version,
                )


def test_subscribers_are_not_called_until_transaction_commits(tmp_path):
    with SQLiteLearningMemory(tmp_path / "learning.sqlite3") as memory:
        events = []
        memory.subscribe(events.append)
        memory.subscribe(lambda _event: (_ for _ in ()).throw(RuntimeError("observer failed")))
        record = memory.put(
            key="candidate.one",
            value={"valid": True},
            department="research",
            provenance="test",
        )
        assert memory.get(record.key) == record
        assert len(events) == 1
        assert events[0].key == record.key


def test_mark_stale_uses_optimistic_version_and_persists(tmp_path):
    database = tmp_path / "learning.sqlite3"
    with SQLiteLearningMemory(database) as memory:
        record = memory.put(
            key="candidate.two",
            value={"edge_bps": 0.4},
            department="analysis",
            provenance="test",
            status="testing",
        )
        stale = memory.mark_stale(record.key, expected_version=record.version)
        assert stale.status == "stale"
        assert stale.version == 2
        with pytest.raises(VersionConflict):
            memory.mark_stale(record.key, expected_version=record.version)

    with SQLiteLearningMemory(database) as reopened:
        assert reopened.get("candidate.two").status == "stale"
        assert [event.status for event in reopened.list_events(key="candidate.two")] == [
            "testing",
            "stale",
        ]



def test_two_connections_serialize_competing_versioned_writes(tmp_path):
    database = tmp_path / "learning-concurrent.sqlite3"
    with SQLiteLearningMemory(database) as seed:
        initial = seed.put(
            key="cross.department.hypothesis",
            value={"value": "initial"},
            department="memory",
            provenance="test",
        )
        assert initial.version == 1

    barrier = threading.Barrier(2)

    def compete(value, department):
        with SQLiteLearningMemory(database) as memory:
            barrier.wait(timeout=5)
            try:
                return memory.put(
                    key="cross.department.hypothesis",
                    value={"value": value},
                    department=department,
                    provenance=f"worker:{department}",
                    expected_version=1,
                )
            except VersionConflict:
                return "version-conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(
            lambda args: compete(*args),
            (("from-radar", "radar"), ("from-analysis", "analysis")),
        ))

    winners = [item for item in results if item != "version-conflict"]
    conflicts = [item for item in results if item == "version-conflict"]
    assert len(winners) == 1
    assert len(conflicts) == 1
    assert winners[0].version == 2

    with SQLiteLearningMemory(database) as reopened:
        current = reopened.get("cross.department.hypothesis")
        assert current == winners[0]
        events = reopened.list_events(key=current.key)
        assert [event.version for event in events] == [1, 2]
        assert [event.event_type for event in events] == ["put", "put"]
