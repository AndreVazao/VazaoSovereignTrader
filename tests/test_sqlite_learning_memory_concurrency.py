from __future__ import annotations

import threading

from PC_ENGINE.learning.shared_memory import VersionConflict
from PC_ENGINE.learning.sqlite_memory import SQLiteLearningMemory


def test_two_connections_cannot_overwrite_same_version_concurrently(tmp_path):
    database = tmp_path / "learning.sqlite3"
    with SQLiteLearningMemory(database) as seed:
        initial = seed.put(
            key="market.edge.btc-usdt",
            value={"edge_bps": 1.0},
            department="analysis",
            provenance="replay:seed",
            status="testing",
        )

    barrier = threading.Barrier(3)
    outcomes: list[tuple[str, int | None]] = []
    outcome_lock = threading.Lock()

    def update(worker: str) -> None:
        with SQLiteLearningMemory(database) as memory:
            barrier.wait(timeout=5)
            try:
                record = memory.put(
                    key=initial.key,
                    value={"worker": worker},
                    department=worker,
                    provenance=f"concurrency-test:{worker}",
                    status="testing",
                    expected_version=initial.version,
                )
                outcome = ("committed", record.version)
            except VersionConflict:
                outcome = ("conflict", None)
            with outcome_lock:
                outcomes.append(outcome)

    workers = [
        threading.Thread(target=update, args=("research",)),
        threading.Thread(target=update, args=("analysis",)),
    ]
    for worker in workers:
        worker.start()
    barrier.wait(timeout=5)
    for worker in workers:
        worker.join(timeout=10)
        assert not worker.is_alive(), "SQLite writer did not finish before timeout"

    assert sorted(kind for kind, _ in outcomes) == ["committed", "conflict"]
    with SQLiteLearningMemory(database) as verify:
        current = verify.get(initial.key)
        assert current is not None
        assert current.version == initial.version + 1
        assert [event.version for event in verify.list_events(key=initial.key)] == [1, 2]
