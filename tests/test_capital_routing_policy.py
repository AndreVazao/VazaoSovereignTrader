from __future__ import annotations

import pytest

from PC_ENGINE.core.capital_routing_policy import CapitalRoutingPolicy


def route(policy: CapitalRoutingPolicy, **overrides):
    args = {
        "source_owner_id": "andre",
        "destination_owner_id": "andre",
        "source_available_quote": 1000,
        "source_baseline_capital_quote": 800,
        "destination_required_quote": 100,
        "expected_net_edge_bps": 12,
        "estimated_transfer_cost_quote": 1,
        "destination_ready": True,
    }
    args.update(overrides)
    return policy.can_route(**args)


def test_same_owner_can_be_eligible():
    ok, reason = route(CapitalRoutingPolicy(owner_id="andre", minimum_transfer_quote=10))
    assert ok is True
    assert reason == "ELIGIBLE"


def test_profit_threshold_must_be_reached_before_routing():
    policy = CapitalRoutingPolicy(
        owner_id="andre",
        minimum_transfer_quote=10,
        capital_plus_profit_pct=0.10,
    )
    ok, reason = route(
        policy,
        source_available_quote=1080,
        source_baseline_capital_quote=1000,
        destination_required_quote=50,
    )
    assert ok is False
    assert reason == "PROFIT_THRESHOLD_NOT_REACHED"

    ok, reason = route(
        policy,
        source_available_quote=1150,
        source_baseline_capital_quote=1000,
        destination_required_quote=50,
    )
    assert ok is True
    assert reason == "ELIGIBLE"


def test_cross_owner_transfer_is_always_blocked():
    policy = CapitalRoutingPolicy(owner_id="andre")
    ok, reason = route(policy, destination_owner_id="genro")
    assert ok is False
    assert reason == "OWNER_BOUNDARY"


def test_no_positive_edge_means_no_transfer():
    policy = CapitalRoutingPolicy(owner_id="andre")
    ok, reason = route(policy, expected_net_edge_bps=0)
    assert ok is False
    assert reason == "NO_POSITIVE_NET_EDGE"


def test_reserve_cash_is_protected():
    policy = CapitalRoutingPolicy(owner_id="andre", reserve_cash_pct=0.5, minimum_transfer_quote=10)
    ok, reason = route(
        policy,
        source_available_quote=100,
        source_baseline_capital_quote=50,
        destination_required_quote=60,
    )
    assert ok is False
    assert reason == "INSUFFICIENT_SURPLUS"


def test_invalid_cross_owner_setting_fails_closed():
    with pytest.raises(ValueError):
        CapitalRoutingPolicy(owner_id="andre", allow_cross_owner_transfer=True).validate()
