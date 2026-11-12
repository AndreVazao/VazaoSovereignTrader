import pytest

from PC_ENGINE.core.platform_connectors import (
    AccessMethod, ConnectorCategory, ConnectorHealth, ConnectorManifest,
)
from PC_ENGINE.core.connector_runtime import ConnectorRegistry


class FakeReadAdapter:
    def __init__(self, response=None, error=None):
        self.response = response if response is not None else {"balance": "paper"}
        self.error = error
        self.calls = []

    def read(self, capability, request):
        self.calls.append((capability, request))
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
    registry.register(manifest(), adapter, owner_grants=grants,
                      provider_verified=grants)
    return registry, adapter


def test_registry_executes_authorized_read_only_adapter():
    registry, adapter = registry_for()
    result = registry.execute_read("uhodler.app", "balances.read", {"account": "main"})
    assert result.ok
    assert result.data == {"balance": "paper"}
    assert adapter.calls == [("balances.read", {"account": "main"})]


def test_registry_denies_missing_owner_grant():
    registry = ConnectorRegistry()
    adapter = FakeReadAdapter()
    registry.register(manifest(), adapter, provider_verified=frozenset({"balances.read"}))
    result = registry.execute_read("uhodler.app", "balances.read")
    assert not result.ok
    assert result.error == "capability_not_authorized"
    assert adapter.calls == []


def test_registry_denies_unverified_provider():
    registry = ConnectorRegistry()
    adapter = FakeReadAdapter()
    registry.register(manifest(), adapter, owner_grants=frozenset({"balances.read"}))
    result = registry.execute_read("uhodler.app", "balances.read")
    assert result.error == "capability_not_authorized"
    assert adapter.calls == []


def test_registry_denies_mutations_before_adapter_call():
    registry, adapter = registry_for()
    result = registry.execute_read("uhodler.app", "orders.create")
    assert result.error == "capability_not_read_only"
    assert adapter.calls == []


def test_registry_denies_unhealthy_connector():
    registry = ConnectorRegistry()
    adapter = FakeReadAdapter()
    registry.register(manifest(health=ConnectorHealth.DEGRADED), adapter,
                      owner_grants=frozenset({"balances.read"}),
                      provider_verified=frozenset({"balances.read"}))
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
    too_large_request = registry.execute_read("uhodler.app", "balances.read", {"x": "a" * 100})
    assert too_large_request.error == "request_too_large"
    assert adapter.calls == []

    registry, _ = registry_for(adapter=FakeReadAdapter({"x": "a" * 100}),
                               max_response_bytes=16)
    too_large_response = registry.execute_read("uhodler.app", "balances.read")
    assert too_large_response.error == "response_too_large"


def test_registry_sanitizes_adapter_exceptions():
    registry, _ = registry_for(adapter=FakeReadAdapter(error="secret-token=do-not-leak"))
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
    assert registry.execute_read("uhodler.app", "balances.read").error == "connector_not_found"
