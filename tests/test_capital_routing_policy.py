from __future__ import annotations

import pytest

from PC_ENGINE.core.capital_routing_policy import CapitalRoutingPolicy


def test_same_owner_can_be_eligible():
    policy = CapitalRoutingPolicy(owner_id="andre", minimum_transfer_quote=10)
    ok, reason = policy.can_route(
        source_owner_id="andre",
        destination_owner_id="andre",
        source_available_quote=1000,
        destination_required_quote=100,
        expected_net_edge_bps=12,
        estimated_transfer_cost_quote=1,
        destination_ready=True,
    )
    assert ok is True
    assert reason == "ELIGIBLE"


def test_cross_owner_transfer_is_always_blocked():
    policy = CapitalRoutingPolicy(owner_id="andre")
    ok, reason = policy.can_route(
        source_owner_id="andre",
        destination_owner_id="genro",
        source_available_quote=1000,
        destination_required_quote=100,
        expected_net_edge_bps=20,
        estimated_transfer_cost_quote=1,
        destination_ready=True,
    )
    assert ok is False
    assert reason == "OWNER_BOUNDARY"


def test_no_positive_edge_means_no_transfer():
    policy = CapitalRoutingPolicy(owner_id="andre")
    ok, reason = policy.can_route(
        source_owner_id="andre",
        destination_owner_id="andre",
        source_available_quote=1000,
        destination_required_quote=100,
        expected_net_edge_bps=0,
        estimated_transfer_cost_quote=1,
        destination_ready=True,
    )
    assert ok is False
    assert reason == "NO_POSITIVE_NET_EDGE"


def test_reserve_cash_is_protected():
    policy = CapitalRoutingPolicy(owner_id="andre", reserve_cash_pct=0.5, minimum_transfer_quote=10)
    ok, reason = policy.can_route(
        source_owner_id="andre",
        destination_owner_id="andre",
        source_available_quote=100,
        destination_required_quote=60,
        expected_net_edge_bps=10,
        estimated_transfer_cost_quote=1,
        destination_ready=True,
    )
    assert ok is False
    assert reason == "INSUFFICIENT_SURPLUS"


def test_invalid_cross_owner_setting_fails_closed():
    with pytest.raises(ValueError):
        CapitalRoutingPolicy(owner_id="andre", allow_cross_owner_transfer=True).validate()
