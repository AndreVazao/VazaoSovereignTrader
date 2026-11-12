from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class ConnectorContractError(ValueError):
    """Raised when a connector manifest or requested capability is unsafe."""


class ConnectorCategory(str, Enum):
    EXCHANGE = "exchange"
    BROKER = "broker"
    FINTECH = "fintech"
    BANKING = "banking"
    WALLET = "wallet"
    PAYMENTS = "payments"
    PORTFOLIO = "portfolio"
    MARKET_DATA = "market_data"
    ANDROID_APP = "android_app"
    WEB_APP = "web_app"
    DESKTOP_APP = "desktop_app"
    CLOUD_SERVICE = "cloud_service"


class AccessMethod(str, Enum):
    OFFICIAL_API = "official_api"
    OAUTH = "oauth"
    OFFICIAL_SDK = "official_sdk"
    USER_EXPORT = "user_export"
    BROWSER_AUTOMATION = "browser_automation"
    ANDROID_AUTOMATION = "android_automation"
    DESKTOP_AUTOMATION = "desktop_automation"
    MANUAL = "manual"


class ConnectorHealth(str, Enum):
    AVAILABLE = "available"
    DEGRADED = "degraded"
    AUTH_REQUIRED = "auth_required"
    RATE_LIMITED = "rate_limited"
    UNSUPPORTED = "unsupported"
    REVOKED = "revoked"
    BLOCKED = "blocked"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


READ_ONLY_CAPABILITIES = frozenset({
    "public_market_data.read",
    "account_identity.read",
    "account_permissions.read",
    "balances.read",
    "transactions.read",
    "positions.read",
    "portfolio.read",
    "statements.read",
    "orders.read",
    "orders.simulate",
    "device.ui.observe",
})

DISABLED_CAPABILITIES = frozenset({
    "orders.create",
    "orders.cancel",
    "funds.transfer",
    "funds.withdraw",
    "profile.manage",
    "device.ui.interact",
})

_PROVIDER_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{1,63}$")
_CAPABILITY = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$")


@dataclass(frozen=True)
class ConnectorManifest:
    provider_id: str
    display_name: str
    category: ConnectorCategory
    access_method: AccessMethod
    capabilities: frozenset[str]
    required_scopes: frozenset[str] = frozenset()
    supported_regions: tuple[str, ...] = ()
    terms_reference: str | None = None
    requests_per_minute: int = 60
    request_timeout_seconds: float = 10.0
    health: ConnectorHealth = ConnectorHealth.UNKNOWN
    adapter_version: str = "0"

    def __post_init__(self) -> None:
        if not _PROVIDER_ID.fullmatch(self.provider_id):
            raise ConnectorContractError("invalid_provider_id")
        if not self.display_name.strip():
            raise ConnectorContractError("display_name_required")
        if not isinstance(self.category, ConnectorCategory):
            raise ConnectorContractError("invalid_connector_category")
        if not isinstance(self.access_method, AccessMethod):
            raise ConnectorContractError("invalid_access_method")
        if not isinstance(self.health, ConnectorHealth):
            raise ConnectorContractError("invalid_connector_health")
        if not self.capabilities.issubset(READ_ONLY_CAPABILITIES):
            raise ConnectorContractError("capability_not_enabled_by_default")
        if any(not _CAPABILITY.fullmatch(item) for item in self.capabilities):
            raise ConnectorContractError("invalid_capability_name")
        if self.requests_per_minute < 1 or self.requests_per_minute > 600:
            raise ConnectorContractError("request_rate_out_of_bounds")
        if not 0.1 <= self.request_timeout_seconds <= 60.0:
            raise ConnectorContractError("request_timeout_out_of_bounds")
        if any(not region or len(region) > 16 for region in self.supported_regions):
            raise ConnectorContractError("invalid_region")


def authorize_capability(manifest: ConnectorManifest, capability: str, *,
                         owner_granted: Iterable[str] = (),
                         provider_verified: Iterable[str] = ()) -> bool:
    """Authorize only a known read-only capability present in all three trust sets.

    The owner grant and provider verification are explicit inputs from trusted
    server-side stores. This helper does not infer grants from client payloads.
    """
    if not isinstance(capability, str) or capability not in READ_ONLY_CAPABILITIES:
        return False
    if manifest.health is not ConnectorHealth.AVAILABLE:
        return False
    return (capability in manifest.capabilities
            and capability in frozenset(owner_granted)
            and capability in frozenset(provider_verified))


def validate_requested_capabilities(capabilities: Iterable[str]) -> frozenset[str]:
    """Normalize a requested capability set and fail closed on unknown/disabled items."""
    requested = frozenset(capabilities)
    if any(not isinstance(item, str) for item in requested):
        raise ConnectorContractError("invalid_capability_name")
    if requested & DISABLED_CAPABILITIES:
        raise ConnectorContractError("capability_disabled")
    if not requested.issubset(READ_ONLY_CAPABILITIES):
        raise ConnectorContractError("unknown_capability")
    return requested


def build_manifest(*, provider_id: str, display_name: str, category: str,
                   access_method: str, capabilities: Iterable[str], **kwargs: object) -> ConnectorManifest:
    """Parse untrusted manifest input into a strictly typed, validated contract."""
    try:
        typed_category = ConnectorCategory(category)
        typed_access = AccessMethod(access_method)
    except ValueError as exc:
        raise ConnectorContractError("unsupported_connector_contract_value") from exc
    typed_capabilities = validate_requested_capabilities(capabilities)
    return ConnectorManifest(
        provider_id=provider_id,
        display_name=display_name,
        category=typed_category,
        access_method=typed_access,
        capabilities=typed_capabilities,
        **kwargs,
    )