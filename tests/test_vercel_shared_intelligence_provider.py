from PC_ENGINE.core.vercel_shared_intelligence_provider import VercelSharedIntelligenceProvider


def test_provider_requires_https_and_credentials():
    import pytest
    with pytest.raises(ValueError, match="not_configured"):
        VercelSharedIntelligenceProvider(base_url="", token="")
    with pytest.raises(ValueError, match="requires_https"):
        VercelSharedIntelligenceProvider(base_url="http://example.test", token="token")


def test_provider_push_uses_public_allowlist_and_skips_expired_artifacts(monkeypatch):
    import time
    provider = VercelSharedIntelligenceProvider(base_url="https://example.test", token="token")
    sent = []
    def fake_request(method, path, payload=None):
        sent.append((method, path, payload))
        return {"ok": True, "accepted": True}
    monkeypatch.setattr(provider, "_request", fake_request)
    now_ms = time.time_ns() // 1_000_000
    base = {
        "schema_version": 1, "artifact_type": "strategy_summary", "strategy_id": "s",
        "market": "BTC/USDT", "regime": "trend", "horizon_seconds": 60,
        "sample_count": 10, "win_count": 6, "win_rate": .6, "mean_net_bps": 2.0,
        "median_net_bps": 1.8, "eligible": True, "created_at_ms": now_ms - 1000,
        "producer_version": "1", "artifact_id": "a", "source_digest": "a" * 64,
        "trust_score": .5, "source_count": 1, "expires_at_ms": now_ms + 60000,
        "source_owner_ref": "private-owner", "source_node_ref": "private-device",
    }
    expired = dict(base, artifact_id="expired", expires_at_ms=now_ms - 1)
    result = provider.push(rows=[{"artifact": base}, {"artifact": expired}])
    assert result["accepted"] == 1
    assert len(sent) == 1
    assert "source_owner_ref" not in sent[0][2]
    assert "source_node_ref" not in sent[0][2]


def test_provider_pull_adapts_cloud_artifact_response(monkeypatch):
    provider = VercelSharedIntelligenceProvider(base_url="https://example.test", token="token")
    artifact = {"strategy_id": "s"}
    monkeypatch.setattr(provider, "_request", lambda *args, **kwargs: {"ok": True, "artifacts": [artifact]})
    result = provider.pull(cursor=None, limit=500)
    assert result["rows"] == [{"artifact": artifact}]
