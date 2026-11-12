from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping


class ExchangeCapabilityError(ValueError):
    """Raised when an exchange operation is outside the explicit read-only policy."""


@dataclass(frozen=True)
class ExchangeReadOnlyPolicy:
    venue: str
    market_type: str
    allowed_operations: frozenset[str]
    forbidden_permissions: frozenset[str]


@dataclass(frozen=True)
class PermissionDecision:
    venue: str
    status: str
    reason: str
    permissions: tuple[tuple[str, bool], ...]

    @property
    def read_only(self) -> bool:
        return self.status == "READ_ONLY"


_READ_OPERATIONS = frozenset({"fetch_balance", "fetch_accounts"})
_FORBIDDEN_PERMISSIONS = frozenset({
    "trade",
    "withdraw",
    "transfer",
    "internal_transfer",
    "margin",
    "futures",
    "derivatives",
    "portfolio_margin",
})

POLICIES: Mapping[str, ExchangeReadOnlyPolicy] = MappingProxyType({
    "binance": ExchangeReadOnlyPolicy(
        venue="binance",
        market_type="spot",
        allowed_operations=_READ_OPERATIONS,
        forbidden_permissions=_FORBIDDEN_PERMISSIONS,
    ),
    "okx": ExchangeReadOnlyPolicy(
        venue="okx",
        market_type="spot",
        allowed_operations=_READ_OPERATIONS,
        forbidden_permissions=_FORBIDDEN_PERMISSIONS,
    ),
})


def get_policy(venue: str) -> ExchangeReadOnlyPolicy:
    name = str(venue or "").strip().lower()
    try:
        return POLICIES[name]
    except KeyError as exc:
        raise ExchangeCapabilityError("unsupported_exchange_venue") from exc


def assert_operation_allowed(venue: str, operation: str) -> None:
    """Allow only named account-read operations; never proxy arbitrary CCXT methods."""
    policy = get_policy(venue)
    name = str(operation or "").strip()
    if name not in policy.allowed_operations:
        raise ExchangeCapabilityError("exchange_operation_not_allowed")


def evaluate_permissions(venue: str, permissions: Mapping[str, object]) -> PermissionDecision:
    """Evaluate an adapter-normalized permission map; incomplete/ambiguous data blocks.

    Adapters must normalize venue-specific permission responses to strict booleans.
    This function does not make network calls and does not infer permissions from
    the mere presence of an API key or a successful balance request.
    """
    policy = get_policy(venue)
    if not isinstance(permissions, Mapping):
        return PermissionDecision(policy.venue, "BLOCKED", "permission_snapshot_invalid", ())

    normalized: dict[str, bool] = {}
    for key, value in permissions.items():
        name = str(key or "").strip().lower()
        if not name or type(value) is not bool:
            return PermissionDecision(policy.venue, "BLOCKED", "permission_snapshot_ambiguous", ())
        if name in normalized:
            return PermissionDecision(policy.venue, "BLOCKED", "permission_snapshot_ambiguous", ())
        normalized[name] = value

    required = {"read", "trade", "withdraw"}
    if not required.issubset(normalized):
        return PermissionDecision(policy.venue, "BLOCKED", "permission_snapshot_incomplete", tuple(sorted(normalized.items())))

    if not normalized["read"]:
        return PermissionDecision(policy.venue, "BLOCKED", "read_permission_missing", tuple(sorted(normalized.items())))

    enabled_forbidden = sorted(
        name for name in policy.forbidden_permissions if normalized.get(name, False)
    )
    if enabled_forbidden:
        return PermissionDecision(
            policy.venue,
            "BLOCKED",
            "forbidden_permission_enabled:" + ",".join(enabled_forbidden),
            tuple(sorted(normalized.items())),
        )

    return PermissionDecision(
        policy.venue,
        "READ_ONLY",
        "read_only_permissions_confirmed",
        tuple(sorted(normalized.items())),
    )
