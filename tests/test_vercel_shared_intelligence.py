from __future__ import annotations

from PC_ENGINE.core.vercel_shared_intelligence import VercelSharedIntelligenceProvider


def test_provider_builds_pull_cursor(monkeypatch):
    provider = VercelSharedIntelligenceProvider("https://intel.example", "secret")
    seen = {}

    def fake_request(method, path, payload=None):
        seen.update(method=method, path=path, payload=payload)
        return {"rows": [], "next_cursor": ""}

    monkeypatch.setattr(provider, "_request", fake_request)
    provider.pull(cursor="abc", limit=600)
    assert seen == {
        "method": "GET",
        "path": "/api/v1/intelligence/pull?limit=500&cursor=abc",
        "payload": None,
    }


def test_provider_push_is_bounded(monkeypatch):
    provider = VercelSharedIntelligenceProvider("https://intel.example", "secret")
    seen = {}

    def fake_request(method, path, payload=None):
        seen.update(method=method, path=path, payload=payload)
        return {"accepted": 500}

    monkeypatch.setattr(provider, "_request", fake_request)
    rows = [{"artifact": {"sample_count": i}} for i in range(600)]
    result = provider.push(rows=rows)
    assert result["accepted"] == 500
    assert len(seen["payload"]["rows"]) == 500
