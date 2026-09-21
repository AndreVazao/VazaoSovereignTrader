from __future__ import annotations

from PC_ENGINE.core.capital_routing_policy import CapitalRoutingPolicy
from PC_ENGINE.core.capital_transfer_planner import CapitalTransferPlanner


def base():
    return {
        "owner_id": "andre",
        "quote_cash": {"USDT": 1500},
        "baseline_capital_quote": {"USDT": 1000},
        "transfer_networks": {"USDT": ["TRC20", "ERC20"]},
    }


def test_planner_selects_private_surplus_for_destination_need():
    planner = CapitalTransferPlanner(CapitalRoutingPolicy(owner_id="andre", capital_plus_profit_pct=0.10, minimum_transfer_quote=10))
    destination = {"venue_id": "okx", "owner_id": "andre", "quote_cash": {"USDT": 20}, "transfer_networks": {"USDT": ["TRC20"]}}
    candidates = planner.plan(owner_id="andre", venues=[{"venue_id": "binance", **base()}, destination], opportunities=[{
        "destination_venue": "okx", "asset": "USDT", "network": "TRC20", "required_quote": 100,
        "expected_net_edge_bps": 20, "estimated_transfer_cost_quote": 1, "estimated_transfer_time_seconds": 30,
        "destination_ready": True,
    }])
    assert len(candidates) == 1
    assert candidates[0].network == "TRC20"
    assert candidates[0].amount_quote == 100


def test_planner_rejects_network_mismatch():
    planner = CapitalTransferPlanner(CapitalRoutingPolicy(owner_id="andre"))
    destination = {"venue_id": "okx", "owner_id": "andre", "transfer_networks": {"USDT": ["ERC20"]}}
    assert planner.plan(owner_id="andre", venues=[{"venue_id": "binance", **base()}, destination], opportunities=[{
        "destination_venue": "okx", "asset": "USDT", "required_quote": 100,
        "expected_net_edge_bps": 20, "estimated_transfer_cost_quote": 1, "destination_ready": True,
    }]) == []


def test_planner_rejects_slow_settlement_for_short_lived_edge():
    planner = CapitalTransferPlanner(CapitalRoutingPolicy(owner_id="andre"))
    destination = {"venue_id": "okx", "owner_id": "andre", "transfer_networks": {"USDT": ["TRC20"]}}
    assert planner.plan(owner_id="andre", venues=[{"venue_id": "binance", **base()}, destination], opportunities=[{
        "destination_venue": "okx", "asset": "USDT", "required_quote": 100,
        "expected_net_edge_bps": 20, "estimated_transfer_cost_quote": 1,
        "estimated_transfer_time_seconds": 600, "max_settlement_seconds": 60, "destination_ready": True,
    }]) == []


def test_planner_never_crosses_owner_boundary():
    planner = CapitalTransferPlanner(CapitalRoutingPolicy(owner_id="andre"))
    destination = {"venue_id": "okx", "owner_id": "genro", "transfer_networks": {"USDT": ["TRC20"]}}
    assert planner.plan(owner_id="andre", venues=[{"venue_id": "binance", **base()}, destination], opportunities=[{
        "destination_venue": "okx", "asset": "USDT", "required_quote": 100,
        "expected_net_edge_bps": 20, "estimated_transfer_cost_quote": 1, "destination_ready": True,
    }]) == []


def test_planner_is_decision_only():
    assert CapitalTransferPlanner.snapshot([])["execution_authority"] == "NONE"
