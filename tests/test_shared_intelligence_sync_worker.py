from PC_ENGINE.core.shared_intelligence import SharedIntelligenceStore
from PC_ENGINE.core.shared_intelligence_sync import SharedIntelligenceSync
from PC_ENGINE.core.shared_intelligence_sync_worker import SharedIntelligenceSyncWorker


class OfflineProvider:
    def pull(self, *, cursor, limit):
        raise RuntimeError("offline")

    def push(self, *, rows):
        raise RuntimeError("offline")


def test_worker_defaults_to_daily_maintenance_intervals(tmp_path):
    store = SharedIntelligenceStore(tmp_path / "artifacts.jsonl")
    sync = SharedIntelligenceSync(store, tmp_path / "sync.json")
    worker = SharedIntelligenceSyncWorker(store, sync, OfflineProvider())
    assert worker.pull_interval == 86400
    assert worker.push_interval == 86400


def test_worker_retry_backoff_is_bounded_and_exponential(tmp_path, monkeypatch):
    store = SharedIntelligenceStore(tmp_path / "artifacts.jsonl")
    sync = SharedIntelligenceSync(store, tmp_path / "sync.json")
    worker = SharedIntelligenceSyncWorker(
        store, sync, OfflineProvider(),
        retry_base_seconds=10, retry_max_seconds=40,
    )
    monkeypatch.setattr("PC_ENGINE.core.shared_intelligence_sync_worker.random.uniform", lambda low, high: high)
    assert worker._retry_delay(1) == 10
    assert worker._retry_delay(2) == 20
    assert worker._retry_delay(3) == 40
    assert worker._retry_delay(10) == 40


def test_worker_jitter_stays_within_configured_interval_bounds(tmp_path, monkeypatch):
    store = SharedIntelligenceStore(tmp_path / "artifacts.jsonl")
    sync = SharedIntelligenceSync(store, tmp_path / "sync.json")
    worker = SharedIntelligenceSyncWorker(
        store, sync, OfflineProvider(), pull_interval_seconds=86400,
        jitter_fraction=0.1,
    )
    monkeypatch.setattr("PC_ENGINE.core.shared_intelligence_sync_worker.random.uniform", lambda low, high: low)
    assert worker._jittered_interval(86400) == 77760
