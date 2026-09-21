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

def test_duplicate_artifact_is_not_appended_twice(tmp_path):
    store = SharedIntelligenceStore(tmp_path / "shared.jsonl")
    first = store.append(artifact())
    second = store.append(artifact())
    assert first == second
    assert len(store.read()) == 1


def test_invalid_source_digest_is_rejected(tmp_path):
    store = SharedIntelligenceStore(tmp_path / "shared.jsonl")
    payload = artifact().to_public_dict()
    payload["source_digest"] = "not-a-sha"
    try:
        store.validate_public_artifact(payload)
    except ValueError as exc:
        assert str(exc) == "invalid_source_digest"
    else:
        raise AssertionError("invalid provenance must be rejected")


def test_importer_rejects_stale_future_and_malformed_artifacts(tmp_path):
    from PC_ENGINE.core.shared_intelligence import SharedIntelligenceImporter

    store = SharedIntelligenceStore(tmp_path / "shared.jsonl")
    now_ms = 100_000
    valid = artifact().to_public_dict()
    valid["created_at_ms"] = now_ms - 1_000
    future = dict(valid)
    future["created_at_ms"] = now_ms + 1_000
    stale = dict(valid)
    stale["created_at_ms"] = now_ms - 90_000_000
    malformed = {"artifact": {"owner_id": "andre", "balance": 1000}}

    result = SharedIntelligenceImporter(store, max_age_ms=10_000).import_rows(
        [valid, future, stale, malformed], now_ms=now_ms
    )
    assert result.accepted == 1
    assert result.skipped == 2
    assert result.rejected == 1
    assert len(store.read()) == 1


def test_shared_artifact_source_trust_and_expiry_are_validated(tmp_path):
    store = SharedIntelligenceStore(tmp_path / "shared.jsonl")
    payload = artifact().to_public_dict()
    payload.update({
        "source_owner_ref": "owner-andre",
        "source_node_ref": "node-pc-01",
        "trust_score": 0.85,
        "source_count": 2,
        "expires_at_ms": 200_000,
    })
    validated = store.validate_public_artifact(payload)
    assert validated["trust_score"] == 0.85
    assert validated["source_count"] == 2

    invalid = dict(payload)
    invalid["trust_score"] = 1.5
    try:
        store.validate_public_artifact(invalid)
    except ValueError as exc:
        assert str(exc) == "invalid_trust_score"
    else:
        raise AssertionError("invalid trust must be rejected")


def test_importer_skips_expired_shared_artifact(tmp_path):
    from PC_ENGINE.core.shared_intelligence import SharedIntelligenceImporter
    store = SharedIntelligenceStore(tmp_path / "shared.jsonl")
    payload = artifact().to_public_dict()
    payload["created_at_ms"] = 99_000
    payload["expires_at_ms"] = 100_000
    result = SharedIntelligenceImporter(store).import_rows([payload], now_ms=100_000)
    assert result.skipped == 1
    assert result.accepted == 0
