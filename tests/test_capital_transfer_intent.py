from __future__ import annotations

import json

from PC_ENGINE.core.capital_transfer_intent import CapitalTransferIntentStore


def test_intent_is_durable_and_idempotent(tmp_path):
    path = tmp_path / "transfers.jsonl"
    store = CapitalTransferIntentStore(path)

    first = store.create(
        owner_id="andre",
        source_venue="binance",
        destination_venue="okx",
        asset="USDT",
        network="TRC20",
        amount_quote=100,
        estimated_cost_quote=1,
        expected_net_edge_bps=20,
    )
    second = store.create(
        owner_id="andre",
        source_venue="binance",
        destination_venue="okx",
        asset="USDT",
        network="TRC20",
        amount_quote=100,
        estimated_cost_quote=1,
        expected_net_edge_bps=20,
    )

    assert first.intent_id == second.intent_id
    assert first.state == "PLANNED"
    assert len(path.read_text().splitlines()) == 1
    row = json.loads(path.read_text().splitlines()[0])
    assert row["owner_id"] == "andre"
    assert row["asset"] == "USDT"
    assert row["network"] == "TRC20"


def test_invalid_intent_fails_closed(tmp_path):
    store = CapitalTransferIntentStore(tmp_path / "transfers.jsonl")
    try:
        store.create(
            owner_id="andre",
            source_venue="binance",
            destination_venue="binance",
            asset="USDT",
            network="TRC20",
            amount_quote=100,
            estimated_cost_quote=1,
            expected_net_edge_bps=20,
        )
    except ValueError:
        return
    assert False, "expected ValueError"


def test_intent_store_has_no_execution_authority(tmp_path):
    snapshot = CapitalTransferIntentStore(tmp_path / "transfers.jsonl").snapshot()
    assert snapshot["execution_authority"] == "NONE"
