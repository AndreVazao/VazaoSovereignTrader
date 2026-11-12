import pytest

from PC_ENGINE.core.platform_connectors import (
    AccessMethod,
    ConnectorCategory,
    ConnectorContractError,
    ConnectorHealth,
    ConnectorManifest,
    authorize_capability,
    build_manifest,
    validate_requested_capabilities,
)


def make_manifest(**overrides):
    values = {
        "provider_id": "uhodler.app",
        "display_name": "U-Hodler",
        "category": ConnectorCategory.FINTECH,
        "access_method": AccessMethod.ANDROID_AUTOMATION,
        "capabilities": frozenset({"portfolio.read", "balances.read"}),
        "health": ConnectorHealth.AVAILABLE,
    }
    values.update(overrides)
    return ConnectorManifest(**values)


def test_manifest_supports_non_exchange_android_fintech_connector():
    manifest = make_manifest()
    assert manifest.category is ConnectorCategory.FINTECH
    assert manifest.access_method is AccessMethod.ANDROID_AUTOMATION
    assert "portfolio.read" in manifest.capabilities


@pytest.mark.parametrize("capability", [
    "orders.create", "orders.cancel", "funds.transfer", "funds.withdraw",
    "profile.manage", "device.ui.interact", "unknown.read",
])
def test_mutation_and_unknown_capabilities_are_rejected(capability):
    with pytest.raises(ConnectorContractError):
        validate_requested_capabilities([capability])


def test_manifest_rejects_unreviewed_capabilities():
    with pytest.raises(ConnectorContractError, match="capability_not_enabled_by_default"):
        make_manifest(capabilities=frozenset({"funds.withdraw"}))


@pytest.mark.parametrize("overrides,reason", [
    ({"provider_id": "Bad ID"}, "invalid_provider_id"),
    ({"display_name": " "}, "display_name_required"),
    ({"requests_per_minute": 0}, "request_rate_out_of_bounds"),
    ({"requests_per_minute": 601}, "request_rate_out_of_bounds"),
    ({"request_timeout_seconds": 0.01}, "request_timeout_out_of_bounds"),
    ({"request_timeout_seconds": 90}, "request_timeout_out_of_bounds"),
    ({"supported_regions": ("",)}, "invalid_region"),
])
def test_manifest_validates_bounds_and_identity(overrides, reason):
    with pytest.raises(ConnectorContractError, match=reason):
        make_manifest(**overrides)


def test_authorization_requires_manifest_owner_and_provider_agreement():
    manifest = make_manifest()
    cap = "balances.read"
    assert authorize_capability(manifest, cap, owner_granted={cap}, provider_verified={cap})
    assert not authorize_capability(manifest, cap, owner_granted=set(), provider_verified={cap})
    assert not authorize_capability(manifest, cap, owner_granted={cap}, provider_verified=set())


def test_unavailable_connector_cannot_authorize_even_with_grants():
    manifest = make_manifest(health=ConnectorHealth.DEGRADED)
    cap = "balances.read"
    assert not authorize_capability(manifest, cap, owner_granted={cap}, provider_verified={cap})


def test_unknown_health_fails_closed():
    manifest = make_manifest(health=ConnectorHealth.UNKNOWN)
    cap = "balances.read"
    assert not authorize_capability(manifest, cap, owner_granted={cap}, provider_verified={cap})


def test_builder_rejects_unknown_category_or_access_method():
    with pytest.raises(ConnectorContractError, match="unsupported_connector_contract_value"):
        build_manifest(provider_id="x1", display_name="X", category="unknown",
                       access_method="official_api", capabilities=[] )


def test_builder_creates_typed_contract_for_cloud_android_or_web():
    manifest = build_manifest(provider_id="cloud.android", display_name="Cloud Android",
        category="android_app", access_method="android_automation",
        capabilities=["device.ui.observe"])
    assert manifest.category is ConnectorCategory.ANDROID_APP
    assert manifest.access_method is AccessMethod.ANDROID_AUTOMATION