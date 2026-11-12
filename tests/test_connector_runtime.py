from concurrent.futures import ThreadPoolExecutor

import pytest

from PC_ENGINE.core.platform_connectors import (
    AccessMethod,
    ConnectorCategory,
    ConnectorHealth,
    ConnectorManifest,
)
from PC_ENGINE.core.connector_runtime import ConnectorRegistry


class FakeReadAdapter:
    def __init__(self, response=None, error=None):
        self.response = response if response is not None else {"balance": "paper"}
        self.error = error
        self.calls = []

    def read(self, capability, request, *, timeout_seconds):
        self.calls.append((capability, request, timeout_seconds))
        if self.error:
            raise RuntimeError(self.error)
        return self.response


def manifest(**overrides):
    values = {
        "provider_id": "uhodler.app",
        "display_name": "U-Hodler",
        "category": ConnectorCategory.FINTECH,
        "access_method": AccessMethod.ANDROID_AUTOMATION,
        "capabilities": frozenset({"balances.read", "portfolio.read"}),
        "health": ConnectorHealth.AVAILABLE,
    }
    values.update(overrides)
    return ConnectorManifest(**values)


def registry_for(adapter=None, **kwargs):
    adapter = adapter or FakeReadAdapter()
    registry = ConnectorRegistry(**kwargs)
    grants = frozenset({"balances.read", "portfolio.read"})
    registry.register(
        manifest(),
        adapter,
        owner_grants=grants,
        provider_verified=grants,
    )
    return registry, adapter


def test_registry_executes_authorized_read_only_adapter():
    registry, adapter = registry_for()
    result = registry.execute_read(
        "uhodler.app", "balances.read", {"account": "main"}
    )
    assert result.ok
    assert result.data == {"balance": "paper"}
    assert adapter.calls == [
        ("balances.read", {"account": "main"}, 10.0)
    ]


def test_registry_passes_manifest_timeout_to_adapter():
    registry = ConnectorRegistry()
    adapter = FakeReadAdapter()
    grants = frozenset({"balances.read"})
    registry.register(
        manifest(request_timeout_seconds=2.5),
        adapter,
        owner_grants=grants,
        provider_verified=grants,
    )

    result = registry.execute_read("uhodler.app", "balances.read")

    assert result.ok
    assert adapter.calls == [("balances.read", {}, 2.5)]


def test_registry_denies_missing_owner_grant():
    registry = ConnectorRegistry()
    adapter = FakeReadAdapter()
    registry.register(
        manifest(),
        adapter,
        provider_verified=frozenset({"balances.read"}),
    )
    result = registry.execute_read("uhodler.app", "balances.read")
    assert not result.ok
    assert result.error == "capability_not_authorized"
    assert adapter.calls == []


def test_registry_denies_unverified_provider():
    registry = ConnectorRegistry()
    adapter = FakeReadAdapter()
    registry.register(
        manifest(),
        adapter,
        owner_grants=frozenset({"balances.read"}),
    )
    result = registry.execute_read("uhodler.app", "balances.read")
    assert result.error == "capability_not_authorized"
    assert adapter.calls == []


def test_registry_rejects_malformed_capability_without_raising():
    registry, adapter = registry_for()
    result = registry.execute_read("uhodler.app", ["balances.read"])
    assert result.error == "capability_not_read_only"
    assert adapter.calls == []


def test_registry_denies_mutations_before_adapter_call():
    registry, adapter = registry_for()
    result = registry.execute_read("uhodler.app", "orders.create")
    assert result.error == "capability_not_read_only"
    assert adapter.calls == []


def test_registry_denies_unhealthy_connector():
    registry = ConnectorRegistry()
    adapter = FakeReadAdapter()
    registry.register(
        manifest(health=ConnectorHealth.DEGRADED),
        adapter,
        owner_grants=frozenset({"balances.read"}),
        provider_verified=frozenset({"balances.read"}),
    )
    result = registry.execute_read("uhodler.app", "balances.read")
    assert result.error == "capability_not_authorized"
    assert adapter.calls == []


def test_registry_rejects_duplicate_provider_and_missing_adapter_method():
    registry = ConnectorRegistry()
    registry.register(manifest(), FakeReadAdapter())
    with pytest.raises(ValueError, match="connector_already_registered"):
        registry.register(manifest(), FakeReadAdapter())
    with pytest.raises(ValueError, match="connector_read_method_required"):
        registry.register(manifest(provider_id="bad.adapter"), object())


def test_registry_bounds_request_and_response_sizes():
    registry, adapter = registry_for(max_request_bytes=16, max_response_bytes=16)
    too_large_request = registry.execute_read(
        "uhodler.app", "balances.read", {"x": "a" * 100}
    )
    assert too_large_request.error == "request_too_large"
    assert adapter.calls == []

    registry, _ = registry_for(
        adapter=FakeReadAdapter({"x": "a" * 100}),
        max_response_bytes=16,
    )
    too_large_response = registry.execute_read("uhodler.app", "balances.read")
    assert too_large_response.error == "response_too_large"


def test_registry_enforces_per_provider_rolling_rate_limit(monkeypatch):
    from PC_ENGINE.core import connector_runtime

    clock = [1000.0]
    monkeypatch.setattr(connector_runtime.time, "monotonic", lambda: clock[0])
    registry = ConnectorRegistry()
    adapter = FakeReadAdapter()
    grants = frozenset({"balances.read"})
    registry.register(
        manifest(requests_per_minute=1),
        adapter,
        owner_grants=grants,
        provider_verified=grants,
    )

    first = registry.execute_read("uhodler.app", "balances.read")
    second = registry.execute_read("uhodler.app", "balances.read")
    clock[0] += 60.01
    after_window = registry.execute_read("uhodler.app", "balances.read")

    assert first.ok
    assert second.error == "rate_limited"
    assert after_window.ok
    assert len(adapter.calls) == 2


def test_registry_rate_limit_is_safe_under_concurrent_calls():
    registry = ConnectorRegistry()
    adapter = FakeReadAdapter()
    grants = frozenset({"balances.read"})
    registry.register(
        manifest(requests_per_minute=1),
        adapter,
        owner_grants=grants,
        provider_verified=grants,
    )

    with ThreadPoolExecutor(max_workers=12) as executor:
        results = list(
            executor.map(
                lambda _: registry.execute_read("uhodler.app", "balances.read"),
                range(12),
            )
        )

    assert sum(result.ok for result in results) == 1
    assert sum(result.error == "rate_limited" for result in results) == 11
    assert len(adapter.calls) == 1


def test_registry_detaches_nested_request_from_caller_owned_state():
    class MutatingAdapter:
        def read(self, capability, request, *, timeout_seconds):
            request["account"]["label"] = "adapter-mutated"
            return {"ok": True}

    registry = ConnectorRegistry()
    grants = frozenset({"balances.read"})
    registry.register(
        manifest(),
        MutatingAdapter(),
        owner_grants=grants,
        provider_verified=grants,
    )
    request = {"account": {"label": "owner-value"}}

    result = registry.execute_read("uhodler.app", "balances.read", request)

    assert result.ok
    assert request == {"account": {"label": "owner-value"}}


def test_registry_sanitizes_adapter_exceptions():
    registry, _ = registry_for(
        adapter=FakeReadAdapter(error="secret-token=do-not-leak")
    )
    result = registry.execute_read("uhodler.app", "balances.read")
    assert result.error == "connector_execution_failed"
    assert "do-not-leak" not in repr(result)


def test_registry_listing_exposes_metadata_but_not_authorization_sets():
    registry, _ = registry_for()
    item = registry.list_connectors()[0]
    assert item["provider_id"] == "uhodler.app"
    assert "owner_grants" not in item
    assert "provider_verified" not in item


def test_registry_unregister_is_idempotent():
    registry, _ = registry_for()
    assert registry.unregister("uhodler.app")
    assert not registry.unregister("uhodler.app")
    assert registry.execute_read(
        "uhodler.app", "balances.read"
    ).error == "connector_not_found"
