from __future__ import annotations

from PC_ENGINE.core.capital_transfer_contract import (
    CapitalTransferContract,
    CapitalTransferResult,
    TransferStatus,
)
from PC_ENGINE.core.capital_transfer_journal import CapitalTransferJournal


class FakeAdapter:
    def __init__(self, result=None, error=None):
        self.calls = 0
        self.result = result or CapitalTransferResult(TransferStatus.CONFIRMED, external_id="tx-1")
        self.error = error

    def transfer(self, intent):
        self.calls += 1
        if self.error:
            raise self.error
        return self.result


def _prepared(contract):
    return contract.prepare(
        owner_id="owner",
        venue_id="venue",
        account_id="account",
        asset="USDT",
        amount=10,
        source="spot",
        destination="funding",
        idempotency_key="transfer-1",
    )


def test_reserve_survives_restart_and_reuses_identity(tmp_path):
    path = tmp_path / "transfers.json"
    first = CapitalTransferJournal(path)
    contract = CapitalTransferContract(owner_id="owner")
    record = _prepared(contract)

    first.reserve(record)
    second = CapitalTransferJournal(path)
    existing = second.reserve(record)

    assert existing.status is TransferStatus.PREPARED
    assert second.get("transfer-1")["status"] == "PREPARED"


def test_submitted_state_survives_restart_and_is_not_retryable(tmp_path):
    path = tmp_path / "transfers.json"
    journal = CapitalTransferJournal(path)
    contract = CapitalTransferContract(owner_id="owner")
    record = _prepared(contract)
    journal.reserve(record)
    submitted = record.__class__(intent=record.intent, status=TransferStatus.SUBMITTED)
    journal.mark_submitted(submitted)

    restored = CapitalTransferJournal(path).get("transfer-1")

    assert restored["status"] == "SUBMITTED"
    assert not contract.can_retry(
        record.__class__(intent=record.intent, status=TransferStatus.SUBMITTED)
    )


def test_unknown_outcome_survives_restart_without_reexecution(tmp_path):
    path = tmp_path / "transfers.json"
    journal = CapitalTransferJournal(path)
    contract = CapitalTransferContract(owner_id="owner")
    record = _prepared(contract)
    journal.reserve(record)
    unknown = record.__class__(
        intent=record.intent,
        status=TransferStatus.UNKNOWN_OUTCOME,
        reason="timeout",
    )
    journal.mark_submitted(
        record.__class__(intent=record.intent, status=TransferStatus.SUBMITTED)
    )
    journal.resolve(unknown)

    restored = CapitalTransferJournal(path).get("transfer-1")

    assert restored["status"] == "UNKNOWN_OUTCOME"
    assert not contract.can_retry(unknown)


def test_confirmed_state_is_terminal_and_cannot_be_downgraded(tmp_path):
    path = tmp_path / "transfers.json"
    journal = CapitalTransferJournal(path)
    contract = CapitalTransferContract(owner_id="owner")
    record = _prepared(contract)
    journal.reserve(record)
    confirmed = record.__class__(
        intent=record.intent,
        status=TransferStatus.CONFIRMED,
        external_id="tx-1",
    )
    journal.resolve(confirmed)

    downgraded = record.__class__(
        intent=record.intent,
        status=TransferStatus.UNKNOWN_OUTCOME,
        reason="late response",
    )
    restored = journal.resolve(downgraded)

    assert restored.status is TransferStatus.CONFIRMED
    assert restored.external_id == "tx-1"
