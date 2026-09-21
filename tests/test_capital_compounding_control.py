from pathlib import Path

from PC_ENGINE.core.capital_compounding_control import CapitalCompoundingController
from PC_ENGINE.core.capital_transfer_accounting import CapitalTransferAccounting
from PC_ENGINE.core.compounding import GlobalCompoundingOrchestrator


def _controller(tmp_path: Path):
    accounting = CapitalTransferAccounting(tmp_path / "accounting.jsonl")
    accounting.apply_confirmed(
        intent_id="intent-1",
        owner_id="andre",
        source_venue="binance",
        destination_venue="bingx",
        asset="USDT",
        amount=10,
        external_reference="tx-1",
    )
    return CapitalCompoundingController(
        owner_id="andre",
        accounting=accounting,
        orchestrator=GlobalCompoundingOrchestrator(
            owner_id="andre", venues=["binance", "bingx"]
        ),
    )


def test_reconciled_capital_unlocks_compounding(tmp_path):
    controller = _controller(tmp_path)
    result = controller.evaluate(
        observed_deltas={
            "binance": {"USDT": -10},
            "bingx": {"USDT": 10},
        },
        equities={"binance": 100, "bingx": 10},
    )
    assert result.routing_allowed is True
    assert result.reason == "CAPITAL_RECONCILED"
    assert result.compounding["global_base"] == 1.0


def test_reconciliation_mismatch_blocks_routing(tmp_path):
    controller = _controller(tmp_path)
    result = controller.evaluate(
        observed_deltas={
            "binance": {"USDT": -9},
            "bingx": {"USDT": 10},
        },
        equities={"binance": 100, "bingx": 10},
    )
    assert result.routing_allowed is False
    assert result.reason == "CAPITAL_RECONCILIATION_MISMATCH"
    assert result.compounding["status"] == "BLOCKED"


def test_controller_is_owner_isolated(tmp_path):
    accounting = CapitalTransferAccounting(tmp_path / "accounting.jsonl")
    other = GlobalCompoundingOrchestrator(owner_id="diogo", venues=["binance"])
    try:
        CapitalCompoundingController(
            owner_id="andre", accounting=accounting, orchestrator=other
        )
    except PermissionError:
        return
    raise AssertionError("expected owner isolation")
