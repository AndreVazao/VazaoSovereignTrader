from __future__ import annotations

from PC_ENGINE.learning.sqlite_memory import SQLiteLearningMemory


def test_over_age_record_is_stale_after_reopening(tmp_path):
    database = tmp_path / "learning.sqlite3"
    now = [1_800_000_000_000_000_000]
    with SQLiteLearningMemory(database, clock_ns=lambda: now[0]) as memory:
        saved = memory.put(
            key="market.edge.eth-usdt",
            value={"net_edge_bps": 1.4},
            department="analysis",
            provenance="replay:freshness-case",
            status="supported",
            confidence=0.8,
        )

    now[0] += 5_000_000_000
    with SQLiteLearningMemory(database, clock_ns=lambda: now[0]) as reopened:
        record = reopened.get(saved.key, max_age_ms=1_000)
        assert record is not None
        assert record.status == "stale"
        assert record.version == saved.version
        assert record.value == saved.value
