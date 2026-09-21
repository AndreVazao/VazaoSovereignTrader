from PC_ENGINE.core.shared_intelligence import SharedIntelligenceStore
from PC_ENGINE.core.shared_intelligence_exporter import export_learning_file


def test_exporter_exports_shared_learning_only(tmp_path):
    source = tmp_path / "learning.jsonl"
    source.write_text(
        '{"strategy_id":"shared_v1","strategy_visibility":"SHARED","market":"BTC/USDT",'
        '"regime":"TREND_UP","horizon_ms":5000,"sample_count":50,"win_count":30,'
        '"win_rate":0.6,"mean_net_bps":2.1,"median_net_bps":1.9,"eligible":true,'
        '"timestamp_ms":12345,"owner_id":"andre","balance":9999}\n'
        '{"strategy_id":"private_v1","strategy_visibility":"PRIVATE","market":"BTC/USDT",'
        '"sample_count":100,"win_count":80}\n',
        encoding="utf-8",
    )
    store = SharedIntelligenceStore(tmp_path / "shared.jsonl")
    assert export_learning_file(source, store, artifact_type="state_outcome") == 1
    row = store.read()[0]["artifact"]
    assert row["strategy_id"] == "shared_v1"
    assert row["horizon_seconds"] == 5
    assert "owner_id" not in row
    assert "balance" not in row


def test_exporter_skips_invalid_rows(tmp_path):
    source = tmp_path / "learning.jsonl"
    source.write_text(
        '{"strategy_id":"bad","strategy_visibility":"SHARED","sample_count":2,"win_count":3}\n',
        encoding="utf-8",
    )
    store = SharedIntelligenceStore(tmp_path / "shared.jsonl")
    assert export_learning_file(source, store, artifact_type="state_outcome") == 0
