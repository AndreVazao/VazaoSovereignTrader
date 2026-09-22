from PC_ENGINE.core.capital_routing_policy import CapitalRoutingPolicy
from PC_ENGINE.core.capital_transfer_planner import CapitalTransferPlanner
from PC_ENGINE.core.compounding import GlobalCompoundingOrchestrator
from PC_ENGINE.core.compounding_routing import CompoundingRoutingBridge


def _bridge():
    policy = CapitalRoutingPolicy(owner_id="andre", minimum_transfer_quote=10.0)
    return CompoundingRoutingBridge(
        orchestrator=GlobalCompoundingOrchestrator(owner_id="andre", venues=["binance", "bingx"]),
        planner=CapitalTransferPlanner(policy),
    )


def test_global_tier_need_feeds_existing_gated_planner():
    bridge = _bridge()
    result = bridge.plan(
        owner_id="andre",
        venues=[
            {"venue_id": "binance", "owner_id": "andre", "equity_quote": 110,
             "quote_cash": {"USDT": 110}, "baseline_capital_quote": {"USDT": 100},
             "transfer_networks": {"USDT": ["TRC20"]}},
            {"venue_id": "bingx", "owner_id": "andre", "equity_quote": 0,
             "quote_cash": {"USDT": 0}, "baseline_capital_quote": {"USDT": 1},
             "transfer_networks": {"USDT": ["TRC20"]}},
        ],
        opportunities=[{
            "destination_venue": "bingx", "asset": "USDT", "required_quote": 10,
            "expected_net_edge_bps": 5, "estimated_transfer_cost_quote": 0.1,
            "destination_ready": True, "destination_whitelisted": True,
            "network": "TRC20", "estimated_transfer_time_seconds": 30,
        }],
    )
    assert result.global_base == 1.0
    assert len(result.candidates) == 1
    assert result.candidates[0].amount_quote == 10.0


def test_bridge_does_not_bypass_whitelist():
    bridge = _bridge()
    result = bridge.plan(
        owner_id="andre",
        venues=[
            {"venue_id": "binance", "owner_id": "andre", "equity_quote": 110,
             "quote_cash": {"USDT": 110}, "baseline_capital_quote": {"USDT": 100},
             "transfer_networks": {"USDT": ["TRC20"]}},
            {"venue_id": "bingx", "owner_id": "andre", "equity_quote": 5,
             "quote_cash": {"USDT": 5}, "baseline_capital_quote": {"USDT": 1},
             "transfer_networks": {"USDT": ["TRC20"]}},
        ],
        opportunities=[{
            "destination_venue": "bingx", "asset": "USDT", "required_quote": 10,
            "expected_net_edge_bps": 5, "estimated_transfer_cost_quote": 0.1,
            "destination_ready": True, "destination_whitelisted": False,
            "network": "TRC20",
        }],
    )
    assert result.candidates == ()


def test_bridge_rejects_cross_owner_destination():
    bridge = _bridge()
    result = bridge.plan(
        owner_id="andre",
        venues=[
            {"venue_id": "binance", "owner_id": "andre", "equity_quote": 110,
             "quote_cash": {"USDT": 110}, "baseline_capital_quote": {"USDT": 100},
             "transfer_networks": {"USDT": ["TRC20"]}},
            {"venue_id": "bingx", "owner_id": "diogo", "equity_quote": 5,
             "quote_cash": {"USDT": 5}, "baseline_capital_quote": {"USDT": 1},
             "transfer_networks": {"USDT": ["TRC20"]}},
        ],
        opportunities=[{
            "destination_venue": "bingx", "asset": "USDT", "required_quote": 10,
            "expected_net_edge_bps": 5, "estimated_transfer_cost_quote": 0.1,
            "destination_ready": True, "destination_whitelisted": True,
            "network": "TRC20",
        }],
    )
    assert result.candidates == ()



def test_bridge_fails_closed_when_confirmed_transfer_deltas_mismatch(tmp_path):
    from PC_ENGINE.core.capital_transfer_accounting import CapitalTransferAccounting
    from PC_ENGINE.core.capital_transfer_reconciliation import CapitalTransferReconciliationGate

    accounting = CapitalTransferAccounting(tmp_path / "accounting.jsonl")
    accounting.apply_confirmed(
        intent_id="tx-1", owner_id="andre", source_venue="binance",
        destination_venue="bingx", asset="USDT", amount=10, external_reference="x1",
    )
    gate = CapitalTransferReconciliationGate(owner_id="andre", accounting=accounting)
    bridge = CompoundingRoutingBridge(
        orchestrator=GlobalCompoundingOrchestrator(owner_id="andre", venues=["binance", "bingx"]),
        planner=CapitalTransferPlanner(CapitalRoutingPolicy(owner_id="andre", minimum_transfer_quote=10.0)),
        reconciliation_gate=gate,
    )
    result = bridge.plan(
        owner_id="andre",
        venues=[
            {"venue_id": "binance", "owner_id": "andre", "equity_quote": 110, "quote_cash": {"USDT": 110}, "baseline_capital_quote": {"USDT": 100}, "transfer_networks": {"USDT": ["TRC20"]}},
            {"venue_id": "bingx", "owner_id": "andre", "equity_quote": 0, "quote_cash": {"USDT": 0}, "baseline_capital_quote": {"USDT": 1}, "transfer_networks": {"USDT": ["TRC20"]}},
        ],
        opportunities=[{"destination_venue": "bingx", "asset": "USDT", "required_quote": 10, "expected_net_edge_bps": 5, "estimated_transfer_cost_quote": 0.1, "destination_ready": True, "destination_whitelisted": True, "network": "TRC20"}],
        observed_transfer_deltas={"binance": {"USDT": -9}, "bingx": {"USDT": 9}},
    )
    assert result.candidates == ()
