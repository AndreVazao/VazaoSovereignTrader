from PC_ENGINE.core.shared_intelligence import SharedIntelligenceArtifact, SharedIntelligenceStore


def artifact():
    return SharedIntelligenceArtifact(
        artifact_type="state_outcome",
        strategy_id="shared_breakout_v1",
        market="BTC/USDT",
        regime="TREND_UP",
        horizon_seconds=60,
        sample_count=100,
        win_count=62,
        win_rate=0.62,
        mean_net_bps=3.2,
        median_net_bps=2.8,
        eligible=True,
        created_at_ms=123,
    )


def test_shared_artifact_contains_no_private_owner_fields(tmp_path):
    store = SharedIntelligenceStore(tmp_path / "shared.jsonl")
    digest = store.append(artifact())
    assert len(digest) == 64
    row = store.read()[0]["artifact"]
    assert "owner_id" not in row
    assert "balance" not in row
    assert "pnl" not in row
    assert "api_key" not in row


def test_private_fields_are_rejected(tmp_path):
    store = SharedIntelligenceStore(tmp_path / "shared.jsonl")
    payload = artifact().to_public_dict()
    payload["owner_id"] = "andre"
    try:
        store.validate_public_artifact(payload)
    except ValueError as exc:
        assert "private_or_unknown_fields" in str(exc)
    else:
        raise AssertionError("private fields must never enter shared intelligence")


def test_tampering_is_detected(tmp_path):
    store = SharedIntelligenceStore(tmp_path / "shared.jsonl")
    store.append(artifact())
    path = tmp_path / "shared.jsonl"
    raw = path.read_text(encoding="utf-8").replace('"mean_net_bps": 3.2', '"mean_net_bps": 99.0')
    path.write_text(raw, encoding="utf-8")
    try:
        store.read()
    except ValueError as exc:
        assert str(exc) == "artifact_integrity_mismatch"
    else:
        raise AssertionError("tampered artifact must be rejected")
