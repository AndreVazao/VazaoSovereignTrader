from PC_ENGINE.core.capital_transfer_accounting import CapitalTransferAccounting


def test_confirmed_transfer_is_idempotent_and_owner_private(tmp_path):
    ledger = CapitalTransferAccounting(tmp_path / "accounting.jsonl")
    first = ledger.apply_confirmed(intent_id="i1", owner_id="andre", source_venue="binance", destination_venue="bingx", asset="USDT", amount=10, external_reference="tx-1")
    second = ledger.apply_confirmed(intent_id="i1", owner_id="andre", source_venue="binance", destination_venue="bingx", asset="USDT", amount=10, external_reference="tx-1")
    assert first == second
    assert ledger.expected_deltas(owner_id="andre") == {"binance": {"USDT": -10.0}, "bingx": {"USDT": 10.0}}


def test_cross_owner_accounting_is_rejected(tmp_path):
    ledger = CapitalTransferAccounting(tmp_path / "accounting.jsonl")
    ledger.apply_confirmed(intent_id="i1", owner_id="andre", source_venue="binance", destination_venue="bingx", asset="USDT", amount=10)
    try:
        ledger.apply_confirmed(intent_id="i1", owner_id="diogo", source_venue="binance", destination_venue="bingx", asset="USDT", amount=10)
    except PermissionError:
        pass
    else:
        raise AssertionError("cross-owner accounting must fail")


def test_observed_deltas_reconcile_against_confirmed_transfers(tmp_path):
    ledger = CapitalTransferAccounting(tmp_path / "accounting.jsonl")
    ledger.apply_confirmed(intent_id="i1", owner_id="andre", source_venue="binance", destination_venue="bingx", asset="USDT", amount=10)
    ok = ledger.reconcile_deltas(owner_id="andre", observed_deltas={"binance": {"USDT": -10}, "bingx": {"USDT": 10}})
    bad = ledger.reconcile_deltas(owner_id="andre", observed_deltas={"binance": {"USDT": -9}, "bingx": {"USDT": 10}})
    assert ok["reconciled"] is True
    assert bad["reconciled"] is False
    assert bad["mismatch_count"] == 1
