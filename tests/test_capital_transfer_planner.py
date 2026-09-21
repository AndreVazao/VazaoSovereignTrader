from __future__ import annotations

from PC_ENGINE.core.capital_routing_policy import CapitalRoutingPolicy
from PC_ENGINE.core.capital_transfer_planner import CapitalTransferPlanner


def test_planner_selects_private_surplus_for_destination_need():
    planner = CapitalTransferPlanner(
        CapitalRoutingPolicy(
            owner_id="andre",
            capital_plus_profit_pct=0.10,
            minimum_transfer_quote=10,
        )
    )
    candidates = planner.plan(
        owner_id="andre",
        venues=[
            {
                "venue_id": "binance",
                "owner_id": "andre",
                "quote_cash": {"USDT": 1500},
                "baseline_capital_quote": {"USDT": 1000},
            },
            {
                "venue_id": "okx",
                "owner_id": "andre",
                "quote_cash": {"USDT": 20},
                "baseline_capital_quote": {"USDT": 20},
            },
        ],
        opportunities=[
            {
                "destination_venue": "okx",
                "asset": "USDT",
                "required_quote": 100,
                "expected_net_edge_bps": 20,
                "estimated_transfer_cost_quote": 1,
                "destination_ready": True,
            }
        ],
    )
    assert len(candidates) == 1
    assert candidates[0].source_venue == "binance"
    assert candidates[0].destination_venue == "okx"
    assert candidates[0].amount_quote == 100


def test_planner_never_crosses_owner_boundary():
    planner = CapitalTransferPlanner(CapitalRoutingPolicy(owner_id="andre"))
    candidates = planner.plan(
        owner_id="andre",
        venues=[
            {
                "venue_id": "binance",
                "owner_id": "andre",
                "quote_cash": {"USDT": 2000},
                "baseline_capital_quote": {"USDT": 1000},
            },
            {
                "venue_id": "okx",
                "owner_id": "genro",
                "quote_cash": {"USDT": 0},
                "baseline_capital_quote": {"USDT": 0},
            },
        ],
        opportunities=[
            {
                "destination_venue": "okx",
                "asset": "USDT",
                "required_quote": 100,
                "expected_net_edge_bps": 20,
                "estimated_transfer_cost_quote": 1,
                "destination_ready": True,
            }
        ],
    )
    assert candidates == []


def test_planner_is_decision_only():
    snapshot = CapitalTransferPlanner.snapshot([])
    assert snapshot["execution_authority"] == "NONE"
    assert snapshot["owner_private"] is True
