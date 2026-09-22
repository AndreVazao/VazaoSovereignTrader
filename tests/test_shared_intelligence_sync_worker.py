from pathlib import Path

from PC_ENGINE.core.shared_intelligence import SharedIntelligenceStore
from PC_ENGINE.core.shared_intelligence_sync import SharedIntelligenceSync


class Provider:
    def __init__(self):
        self.pulls = []
        self.pushes = []

    def pull(self, *, cursor, limit):
        self.pulls.append((cursor, limit))
        return {"rows": [], "next_cursor": "c1"}

    def push(self, *, rows):
        self.pushes.append(rows)
        return {"accepted": len(rows), "next_cursor": "c2"}


def test_sync_worker_contract(tmp_path: Path):
    from PC_ENGINE.core.shared_intelligence_sync_worker import (
        SharedIntelligenceSyncWorker,
    )

    provider = Provider()
    store = SharedIntelligenceStore(tmp_path / "artifacts.jsonl")
    sync = SharedIntelligenceSync(store, tmp_path / "state.json")
    worker = SharedIntelligenceSyncWorker(
        store,
        sync,
        provider,
        pull_interval_seconds=1,
        push_interval_seconds=1,
    )

    result = worker.run_once(bootstrap=True)

    assert result["pull"]["accepted"] == 0
    assert provider.pulls[0][0] is None
    assert worker.bootstrap_done is True
