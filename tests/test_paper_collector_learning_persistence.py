from __future__ import annotations

from pathlib import Path

from PC_ENGINE.learning.memory_backup import (
    backup_learning_memory,
    restore_learning_memory_backup,
)
from PC_ENGINE.learning.sqlite_memory import SQLiteLearningMemory
from PC_ENGINE.services.paper_market_collector import PaperMarketCollector


class _UnusedStrategy:
    def analyse(self, *_args, **_kwargs):
        raise AssertionError("the persistence test injects deterministic market states")


def _states() -> list[dict]:
    common = {
        "symbol": "BTC/USDT",
        "regime": "TREND",
        "trend": "UP",
        "volatility": "LOW",
        "confluence_score": 0.8,
        "confluence_confidence": 0.9,
        "technical_score": 0.8,
        "candlestick_bias": 0.2,
        "radar_pressure": 0.1,
        "lead_lag_score": 0.0,
        "momentum_score": 0.7,
        "mean_reversion_score": 0.0,
        "order_flow_score": 0.1,
        "breakout_score": 0.2,
        "derivatives_score": 0.0,
    }
    return [
        {**common, "timestamp_ms": 1_000, "price": 100.0, "action": "BUY"},
        {**common, "timestamp_ms": 3_000, "price": 101.0, "action": "HOLD"},
    ]


def test_paper_collector_learning_survives_restart_and_verified_backup_restore(tmp_path: Path):
    database = tmp_path / "owner" / "learning.sqlite3"
    backup = tmp_path / "backups" / "learning.sqlite3"
    restored = tmp_path / "recovery" / "learning.sqlite3"
    memory = SQLiteLearningMemory(database)
    collector = PaperMarketCollector(
        settings={
            "polling_exchanges": [],
            "data_dir": str(tmp_path / "radar"),
            "learning_min_samples": 1,
            "learning_horizons_ms": [1_000],
            "learning_cost_bps": 0,
            "confluence": {
                "data_dir": str(tmp_path / "radar"),
                "derivatives": {"enabled": False, "observational_only": True},
            },
        },
        symbols=["BTC/USDT"],
        ohlcv_fetcher=lambda *_args: [],
        strategy=_UnusedStrategy(),
        learning_memory=memory,
    )
    collector.state_store.recent = lambda limit: _states()

    try:
        collector._refresh_learning()
        first_records = tuple(memory.iter_records())
        learning_records = [
            record for record in first_records
            if record.key.startswith("paper.market_state.")
        ]
        assert learning_records
        assert {record.value["kind"] for record in learning_records} == {
            "state_signature", "state_outcome"
        }
        assert all(record.status == "unverified" for record in learning_records)
        assert all(record.confidence == 0.0 for record in learning_records)
        assert all(record.value["paper_only"] is True for record in learning_records)
        assert all(record.value["execution_authorized"] is False for record in learning_records)

        versions_before = {record.key: record.version for record in learning_records}
        event_count_before = len(memory.list_events(limit=1000))
        persisted_before = collector.durable_learning_persisted

        collector._refresh_learning()

        refreshed = {
            record.key: record.version
            for record in memory.iter_records()
            if record.key.startswith("paper.market_state.")
        }
        assert refreshed == versions_before
        assert collector.durable_learning_persisted == persisted_before
        assert collector.durable_learning_duplicates > 0
        assert len(memory.list_events(limit=1000)) == event_count_before
    finally:
        collector.stop()
        memory.close()

    backup_learning_memory(database, backup)
    restore_learning_memory_backup(backup, restored)

    with SQLiteLearningMemory(restored) as recovered:
        recovered_records = [
            record for record in recovered.iter_records()
            if record.key.startswith("paper.market_state.")
        ]
        assert recovered_records
        assert {record.key for record in recovered_records} == set(versions_before)
        assert all(record.status == "unverified" for record in recovered_records)
        assert len(recovered.list_events(limit=1000)) == event_count_before
