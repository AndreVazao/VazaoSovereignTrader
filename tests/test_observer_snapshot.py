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
        health_state="healthy",
        allow_new_tasks=True,
        allow_risk_bearing_actions=True,
        health_checked_at_ms=1000,
    )
    mailbox.publish(
        status="PAUSED",
        mode="PAPER",
        open_positions_count=1,
        opportunities_count=3,
        updated_at_ms=456,
        health_state="degraded",
        allow_new_tasks=False,
        allow_risk_bearing_actions=True,
        health_checked_at_ms=2000,
    )

    payload = mailbox.read()
    assert payload == {
        "ok": True,
        "status": "PAUSED",
        "mode": "PAPER",
        "open_positions_count": 1,
        "opportunities_count": 3,
        "updated_at_ms": 456,
        "health_state": "degraded",
        "allow_new_tasks": False,
        "allow_risk_bearing_actions": False,
        "health_checked_at_ms": 2000,
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
        health_state=None,
        allow_new_tasks="false",
        allow_risk_bearing_actions=True,
        health_checked_at_ms=-1,
    )
    payload = mailbox.read()

    assert set(payload) == {
        "ok",
        "status",
        "mode",
        "open_positions_count",
        "opportunities_count",
        "updated_at_ms",
        "health_state",
        "allow_new_tasks",
        "allow_risk_bearing_actions",
        "health_checked_at_ms",
    }
    assert payload["status"] == "None"
    assert payload["open_positions_count"] == 0
    assert payload["opportunities_count"] == 4
    assert payload["health_state"] == "None"
    assert payload["allow_new_tasks"] is False
    assert payload["allow_risk_bearing_actions"] is False
    assert payload["health_checked_at_ms"] == 0
    assert all(
        isinstance(payload[key], (str, int, bool))
        for key in payload
    )


def test_observer_snapshot_bounds_text_and_normalizes_invalid_numbers():
    mailbox = RuntimeObserverSnapshot()
    oversized = "x" * 10_000

    mailbox.publish(
        status=oversized,
        mode=oversized,
        open_positions_count="not-a-number",
        opportunities_count=None,
        updated_at_ms="invalid",
        health_state=oversized,
        allow_new_tasks=True,
        allow_risk_bearing_actions=True,
        health_checked_at_ms="invalid",
    )

    payload = mailbox.read()
    assert payload["status"] == "x" * 48
    assert payload["mode"] == "x" * 48
    assert payload["health_state"] == "x" * 48
    assert payload["open_positions_count"] == 0
    assert payload["opportunities_count"] == 0
    assert payload["updated_at_ms"] > 0
    assert payload["health_checked_at_ms"] == 0
    assert payload["allow_new_tasks"] is True
    assert payload["allow_risk_bearing_actions"] is False
    assert sum(len(value) for value in payload.values() if isinstance(value, str)) <= 144
