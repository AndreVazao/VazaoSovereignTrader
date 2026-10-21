from __future__ import annotations

import threading

from PC_ENGINE.core.observer_snapshot import RuntimeObserverSnapshot


def test_observer_snapshot_remains_bounded_under_concurrent_readers_and_publishers():
    mailbox = RuntimeObserverSnapshot()
    stop = threading.Event()
    failures: list[str] = []
    schema = {
        "ok",
        "status",
        "mode",
        "open_positions_count",
        "opportunities_count",
        "updated_at_ms",
    }

    def reader() -> None:
        while not stop.is_set():
            payload = mailbox.read()
            if set(payload) != schema:
                failures.append("schema changed")
                stop.set()
                return
            if not isinstance(payload["status"], str):
                failures.append("status is not a string")
                stop.set()
                return
            if payload["open_positions_count"] < 0 or payload["opportunities_count"] < 0:
                failures.append("negative normalized count")
                stop.set()
                return

    readers = [threading.Thread(target=reader, daemon=True) for _ in range(4)]
    for thread in readers:
        thread.start()

    try:
        for index in range(5000):
            mailbox.publish(
                status="RUNNING" if index % 2 else "PAUSED",
                mode="PAPER",
                open_positions_count=index % 7,
                opportunities_count=index % 13,
                updated_at_ms=index + 1,
            )
        latest = mailbox.read()
        assert latest["updated_at_ms"] == 5000
        assert latest["open_positions_count"] == 4999 % 7
        assert latest["opportunities_count"] == 4999 % 13
        assert not failures
    finally:
        stop.set()
        for thread in readers:
            thread.join(timeout=1)

    assert all(not thread.is_alive() for thread in readers)
    # The mailbox is latest-value only: its retained payload has a fixed schema
    # regardless of how many updates were published.
    assert set(mailbox.read()) == schema
