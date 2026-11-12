from __future__ import annotations

import pytest

from PC_ENGINE.core.exchange_capabilities import (
    ExchangeCapabilityError,
    assert_operation_allowed,
    evaluate_permissions,
    get_policy,
)


@pytest.mark.parametrize("venue", ["binance", "okx"])
def test_supported_venues_are_spot_and_have_narrow_read_allowlist(venue):
    policy = get_policy(venue)
    assert policy.market_type == "spot"
    assert policy.allowed_operations == frozenset({"fetch_balance", "fetch_accounts"})
    assert_operation_allowed(venue, "fetch_balance")
    assert_operation_allowed(venue, "fetch_accounts")


@pytest.mark.parametrize("operation", [
    "create_order", "create_market_order", "cancel_order", "cancel_all_orders",
    "withdraw", "transfer", "sapi_post_withdraw", "private_post_trade_order",
    "fetch_positions", "fetch_open_orders", "load_markets",
])
def test_trade_transfer_and_unreviewed_operations_are_denied(operation):
    with pytest.raises(ExchangeCapabilityError, match="exchange_operation_not_allowed"):
        assert_operation_allowed("binance", operation)


def test_unknown_venue_fails_closed():
    with pytest.raises(ExchangeCapabilityError, match="unsupported_exchange_venue"):
        get_policy("coinbase")


@pytest.mark.parametrize("venue", ["binance", "okx"])
def test_explicit_read_only_permissions_are_accepted(venue):
    decision = evaluate_permissions(venue, {
        "read": True,
        "trade": False,
        "withdraw": False,
    })
    assert decision.read_only is True
    assert decision.status == "READ_ONLY"
    assert decision.reason == "read_only_permissions_confirmed"


@pytest.mark.parametrize("permissions,reason", [
    ({"read": True, "trade": True, "withdraw": False}, "forbidden_permission_enabled:trade"),
    ({"read": True, "trade": False, "withdraw": True}, "forbidden_permission_enabled:withdraw"),
    ({"read": True, "trade": False, "withdraw": False, "transfer": True}, "forbidden_permission_enabled:transfer"),
    ({"read": False, "trade": False, "withdraw": False}, "read_permission_missing"),
    ({"read": True, "trade": False}, "permission_snapshot_incomplete"),
    ({"read": 1, "trade": False, "withdraw": False}, "permission_snapshot_ambiguous"),
    ({"read": True, "trade": False, "withdraw": False, "margin": "false"}, "permission_snapshot_ambiguous"),
])
def test_unsafe_or_ambiguous_permission_snapshots_are_blocked(permissions, reason):
    decision = evaluate_permissions("okx", permissions)
    assert decision.read_only is False
    assert decision.status == "BLOCKED"
    assert decision.reason == reason


def test_non_mapping_permission_payload_is_blocked():
    decision = evaluate_permissions("binance", None)
    assert decision.status == "BLOCKED"
    assert decision.reason == "permission_snapshot_invalid"


def test_permission_decision_contains_no_secret_values():
    decision = evaluate_permissions("binance", {
        "read": True, "trade": False, "withdraw": False,
    })
    assert "api_key" not in dict(decision.permissions)
    assert "api_secret" not in dict(decision.permissions)
