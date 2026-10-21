from __future__ import annotations

from PC_ENGINE.core.observer_snapshot import RuntimeObserverSnapshot


def test_observer_snapshot_keeps_only_latest_primitive_payload():
    mailbox = RuntimeObserverSnapshot()

    mailbox.publish(
        status="RUNNING",
        mode="PAPER",
        open_positions_count=2,
        opportunities_count=8,
        updated_at_ms=123,
    )
    mailbox.publish(
        status="PAUSED",
        mode="PAPER",
        open_positions_count=1,
        opportunities_count=3,
        updated_at_ms=456,
    )

    payload = mailbox.read()
    assert payload == {
        "ok": True,
        "status": "PAUSED",
        "mode": "PAPER",
        "open_positions_count": 1,
        "opportunities_count": 3,
        "updated_at_ms": 456,
    }

    # A reader cannot mutate the cached value by changing its copy.
    payload["status"] = "CORRUPTED"
    assert mailbox.read()["status"] == "PAUSED"


def test_observer_snapshot_normalizes_counts_and_keeps_fixed_schema():
    mailbox = RuntimeObserverSnapshot()

    mailbox.publish(
        status=None,
        mode="PAPER",
        open_positions_count=-5,
        opportunities_count="4",
        updated_at_ms=789,
    )
    payload = mailbox.read()

    assert set(payload) == {
        "ok",
        "status",
        "mode",
        "open_positions_count",
        "opportunities_count",
        "updated_at_ms",
    }
    assert payload["status"] == "None"
    assert payload["open_positions_count"] == 0
    assert payload["opportunities_count"] == 4
    assert all(
        isinstance(payload[key], (str, int, bool))
        for key in payload
    )
