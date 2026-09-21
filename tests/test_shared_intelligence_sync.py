from PC_ENGINE.core.shared_intelligence import SharedIntelligenceArtifact, SharedIntelligenceStore
from PC_ENGINE.core.shared_intelligence_sync import SharedIntelligenceSync


class Provider:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def pull(self, *, cursor, limit):
        self.calls.append((cursor, limit))
        return {"rows": self.rows, "next_cursor": "cursor-1"}

    def push(self, *, rows):
        return {"accepted": len(rows), "next_cursor": "cursor-2"}


def row(ts=1000):
    return {"artifact": SharedIntelligenceArtifact(
        artifact_type="state_outcome", strategy_id="s", market="BTC/USDT", regime="TREND_UP",
        horizon_seconds=60, sample_count=10, win_count=6, win_rate=.6, mean_net_bps=2.0,
        median_net_bps=1.8, eligible=True, created_at_ms=ts, source_node_ref="node-a"
    ).to_public_dict()}


def test_bootstrap_downloads_full_snapshot_and_persists_cursor(tmp_path):
    store = SharedIntelligenceStore(tmp_path / "shared.jsonl")
    provider = Provider([row()])
    sync = SharedIntelligenceSync(store, tmp_path / "sync.json")
    result = sync.bootstrap(provider, now_ms=2000)
    assert result["accepted"] == 1
    assert provider.calls[0][0] is None
    assert "cursor-1" in (tmp_path / "sync.json").read_text()


def test_incremental_sync_uses_persisted_cursor(tmp_path):
    store = SharedIntelligenceStore(tmp_path / "shared.jsonl")
    provider = Provider([row()])
    sync = SharedIntelligenceSync(store, tmp_path / "sync.json")
    sync.bootstrap(provider, now_ms=2000)
    sync.sync_once(provider, now_ms=3000)
    assert provider.calls[-1][0] == "cursor-1"


def test_provider_failure_does_not_break_local_store(tmp_path):
    store = SharedIntelligenceStore(tmp_path / "shared.jsonl")
    sync = SharedIntelligenceSync(store, tmp_path / "sync.json")
    class Broken:
        def pull(self, **kwargs): raise RuntimeError("offline")
        def push(self, **kwargs): raise RuntimeError("offline")
    assert sync.sync_once(Broken(), now_ms=2000) == {"accepted": 0, "rejected": 0, "skipped": 0}
