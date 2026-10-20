from __future__ import annotations

import pytest

from PC_ENGINE.learning.shared_memory import SharedLearningMemory, VersionConflict


def test_departments_read_same_versioned_record_and_receive_change_event():
    memory = SharedLearningMemory()
    observed = []
    memory.subscribe(observed.append)

    first = memory.put(
        key="temporal.btc-usdt.binance-coinbase",
        value={"net_edge_bps": 3.2},
        department="analysis",
        provenance="synthetic-replay:run-001",
        status="testing",
        confidence=0.6,
    )
    research_view = memory.get(first.key)
    risk_view = memory.get(first.key)

    assert research_view == risk_view == first
    assert first.version == 1
    assert observed[0].key == first.key
    assert observed[0].version == 1
    assert observed[0].event_type == "put"


def test_version_conflict_prevents_stale_department_overwrite():
    memory = SharedLearningMemory()
    record = memory.put(
        key="hypothesis.alpha",
        value="candidate",
        department="research",
        provenance="test",
    )
    memory.put(
        key=record.key,
        value="updated",
        department="analysis",
        provenance="test",
        expected_version=record.version,
    )

    with pytest.raises(VersionConflict):
        memory.put(
            key=record.key,
            value="stale-overwrite",
            department="research",
            provenance="test",
            expected_version=record.version,
        )
    assert memory.get(record.key).value == "updated"
    assert memory.get(record.key).version == 2


def test_expired_or_old_evidence_is_returned_as_stale():
    now = [1_000_000_000]
    memory = SharedLearningMemory(clock_ns=lambda: now[0])
    record = memory.put(
        key="venue.edge",
        value=1,
        department="analysis",
        provenance="synthetic",
        status="supported",
        confidence=0.95,
        ttl_ms=10,
    )

    now[0] += 11_000_000
    assert memory.get(record.key).status == "stale"
    assert memory.get(record.key, max_age_ms=1).status == "stale"
    assert memory.list_records(status="stale")[0].key == record.key
    assert memory.list_records(status="supported") == ()


def test_freshness_windows_require_integer_milliseconds():
    memory = SharedLearningMemory()
    with pytest.raises(ValueError, match="ttl_ms"):
        memory.put(
            key="bad-ttl",
            value=1,
            department="research",
            provenance="test",
            ttl_ms=1.5,
        )
    with pytest.raises(ValueError, match="max_age_ms"):
        memory.get("missing", max_age_ms=0.5)


def test_invalid_confidence_or_status_is_rejected():
    memory = SharedLearningMemory()
    with pytest.raises(ValueError, match="confidence"):
        memory.put(
            key="x",
            value=1,
            department="analysis",
            provenance="test",
            confidence=float("nan"),
        )
    with pytest.raises(ValueError, match="status"):
        memory.put(
            key="x",
            value=1,
            department="analysis",
            provenance="test",
            status="approved-for-live",
        )


def test_subscriber_failure_does_not_undo_committed_record():
    memory = SharedLearningMemory()
    memory.subscribe(lambda _event: (_ for _ in ()).throw(RuntimeError("observer failed")))
    record = memory.put(
        key="durable-to-process",
        value="committed",
        department="research",
        provenance="test",
    )
    assert memory.get(record.key) == record


def test_unsubscribe_stops_future_notifications():
    memory = SharedLearningMemory()
    events = []
    unsubscribe = memory.subscribe(events.append)
    memory.put(key="one", value=1, department="research", provenance="test")
    unsubscribe()
    memory.put(key="two", value=2, department="research", provenance="test")
    assert [event.key for event in events] == ["one"]
