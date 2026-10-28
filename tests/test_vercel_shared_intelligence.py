import time

import pytest

from PC_ENGINE.core.vercel_shared_intelligence import VercelSharedIntelligenceProvider


def test_provider_requires_https_and_credentials():
    with pytest.raises(ValueError, match="not_configured"):
        VercelSharedIntelligenceProvider("", "")
    with pytest.raises(ValueError, match="requires_https"):
        VercelSharedIntelligenceProvider("http://example.test", "token")


def test_provider_push_uses_public_allowlist_and_skips_expired_artifacts(monkeypatch):
    provider = VercelSharedIntelligenceProvider("https://example.test", "token")
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
    assert sent[0][0:2] == ("POST", "/api/v1/artifacts")
    assert "source_owner_ref" not in sent[0][2]
    assert "source_node_ref" not in sent[0][2]


def test_provider_pull_adapts_cloud_snapshot(monkeypatch):
    provider = VercelSharedIntelligenceProvider("https://example.test", "token")
    artifact = {"strategy_id": "s"}
    calls = []
    def fake_request(method, path, payload=None):
        calls.append((method, path))
        return {"ok": True, "artifacts": [artifact]}
    monkeypatch.setattr(provider, "_request", fake_request)
    result = provider.pull(cursor=None, limit=500)
    assert calls == [("GET", "/api/v1/artifacts?limit=100")]
    assert result["rows"] == [{"artifact": artifact}]

def test_verified_push_signs_exact_public_payload_and_uses_provenance_endpoint(monkeypatch):
    import base64

    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    from PC_ENGINE.core.canonical_json import canonicalize_provenance_message, digest_public_payload
    from PC_ENGINE.core.shared_learning_provenance import VerifiedProvenanceSigner

    private_key = Ed25519PrivateKey.generate()
    private_pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    signer = VerifiedProvenanceSigner(
        organization_id="123e4567-e89b-42d3-a456-426614174000",
        installation_id="223e4567-e89b-42d3-a456-426614174000",
        agent_id="323e4567-e89b-42d3-a456-426614174000",
        department_id="423e4567-e89b-42d3-a456-426614174000",
        private_key_pem=private_pem,
    )
    provider = VercelSharedIntelligenceProvider("https://example.test", "token")
    sent = []

    def fake_request(method, path, payload=None):
        sent.append((method, path, payload))
        return {"ok": True, "accepted": True, "provenance": "verified"}

    monkeypatch.setattr(provider, "_request", fake_request)
    now_ms = time.time_ns() // 1_000_000
    artifact = {
        "schema_version": 1, "artifact_type": "strategy_summary", "strategy_id": "s",
        "market": "BTC/USDT", "regime": "trend", "horizon_seconds": 60,
        "sample_count": 10, "win_count": 6, "win_rate": .6, "mean_net_bps": 2.0,
        "median_net_bps": 1.8, "eligible": True, "created_at_ms": now_ms - 1000,
        "producer_version": "1", "artifact_id": "artifact-verified-1", "source_digest": "a" * 64,
        "trust_score": .5, "source_count": 1, "expires_at_ms": now_ms + 60000,
        "source_owner_ref": "private-owner", "source_node_ref": "private-device",
    }

    result = provider.push_verified(
        rows=[{"artifact": artifact, "source_artifact_ids": ["source-public-1"]}],
        signer=signer,
    )

    assert result["accepted"] == 1
    assert len(sent) == 1
    method, path, body = sent[0]
    assert (method, path) == ("POST", "/api/v1/artifacts")
    assert set(body) == {"artifact", "provenance"}
    assert "source_owner_ref" not in body["artifact"]
    assert "source_node_ref" not in body["artifact"]
    envelope = body["provenance"]
    assert envelope["payload_digest"] == digest_public_payload(body["artifact"])
    assert envelope["source_artifact_ids"] == ["source-public-1"]
    signature = base64.urlsafe_b64decode(
        envelope["signature"] + "=" * (-len(envelope["signature"]) % 4)
    )
    private_key.public_key().verify(signature, canonicalize_provenance_message(envelope))


def test_verified_push_requires_explicit_lineage_and_never_falls_back(monkeypatch):
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    from PC_ENGINE.core.shared_learning_provenance import VerifiedProvenanceSigner

    private_pem = Ed25519PrivateKey.generate().private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    signer = VerifiedProvenanceSigner(
        organization_id="123e4567-e89b-42d3-a456-426614174000",
        installation_id="223e4567-e89b-42d3-a456-426614174000",
        agent_id="323e4567-e89b-42d3-a456-426614174000",
        department_id="423e4567-e89b-42d3-a456-426614174000",
        private_key_pem=private_pem,
    )
    provider = VercelSharedIntelligenceProvider("https://example.test", "token")
    calls = []
    monkeypatch.setattr(provider, "_request", lambda *args, **kwargs: calls.append(args) or {
        "ok": True, "accepted": True, "provenance": "legacy_unattributed"
    })
    now_ms = time.time_ns() // 1_000_000
    artifact = {
        "schema_version": 1, "artifact_type": "strategy_summary", "strategy_id": "s",
        "market": "BTC/USDT", "regime": "trend", "horizon_seconds": 60,
        "sample_count": 10, "win_count": 6, "win_rate": .6, "mean_net_bps": 2.0,
        "median_net_bps": 1.8, "eligible": True, "created_at_ms": now_ms - 1000,
        "producer_version": "1", "artifact_id": "artifact-verified-2", "source_digest": "a" * 64,
        "trust_score": .5, "source_count": 1, "expires_at_ms": now_ms + 60000,
    }

    with pytest.raises(ValueError, match="source_ids_required"):
        provider.push_verified(rows=[{"artifact": artifact}], signer=signer)
    assert calls == []

    with pytest.raises(RuntimeError, match="verified_provenance_not_confirmed"):
        provider.push_verified(
            rows=[{"artifact": artifact, "source_artifact_ids": []}],
            signer=signer,
        )
    assert len(calls) == 1

