from PC_ENGINE.core.capital_routing_policy import CapitalRoutingPolicy


def test_automatic_same_owner_routing_does_not_wait_for_per_transfer_approval():
    policy = CapitalRoutingPolicy(owner_id="andre")
    ok, reason = policy.can_route(
        source_owner_id="andre",
        destination_owner_id="andre",
        source_available_quote=110,
        source_baseline_capital_quote=100,
        destination_required_quote=10,
        expected_net_edge_bps=20,
        estimated_transfer_cost_quote=0.10,
        destination_ready=True,
        destination_whitelisted=True,
    )
    assert ok is True
    assert reason == "ELIGIBLE"
    assert policy.snapshot()["execution_authority"] == "AUTO_SAME_OWNER"


def test_automatic_routing_still_fails_closed_without_whitelist():
    policy = CapitalRoutingPolicy(owner_id="andre")
    ok, reason = policy.can_route(
        source_owner_id="andre",
        destination_owner_id="andre",
        source_available_quote=110,
        source_baseline_capital_quote=100,
        destination_required_quote=10,
        expected_net_edge_bps=20,
        estimated_transfer_cost_quote=0.10,
        destination_ready=True,
        destination_whitelisted=False,
    )
    assert ok is False
    assert reason == "DESTINATION_NOT_WHITELISTED"


def test_cross_owner_remains_forbidden():
    policy = CapitalRoutingPolicy(owner_id="andre")
    ok, reason = policy.can_route(
        source_owner_id="andre",
        destination_owner_id="genro",
        source_available_quote=110,
        source_baseline_capital_quote=100,
        destination_required_quote=10,
        expected_net_edge_bps=20,
        estimated_transfer_cost_quote=0.10,
        destination_ready=True,
        destination_whitelisted=True,
    )
    assert ok is False
    assert reason == "OWNER_BOUNDARY"
