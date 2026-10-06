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
    existing = CapitalTransferJournal(path).reserve(record)

    assert existing.status is TransferStatus.PREPARED
    assert existing.intent.idempotency_key == "transfer-1"


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
    assert not contract.can_retry(submitted)


def test_unknown_outcome_survives_restart_without_reexecution(tmp_path):
    path = tmp_path / "transfers.json"
    journal = CapitalTransferJournal(path)
    contract = CapitalTransferContract(owner_id="owner")
    record = _prepared(contract)
    journal.reserve(record)
    submitted = record.__class__(intent=record.intent, status=TransferStatus.SUBMITTED)
    journal.mark_submitted(submitted)
    unknown = record.__class__(
        intent=record.intent,
        status=TransferStatus.UNKNOWN_OUTCOME,
        reason="timeout",
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


def test_execute_persists_and_resolves_confirmation(tmp_path):
    path = tmp_path / "transfers.json"
    adapter = FakeAdapter()
    journal = CapitalTransferJournal(path)
    contract = CapitalTransferContract(
        owner_id="owner",
        adapter=adapter,
        transfer_authorizer=lambda _: True,
        journal=journal,
    )

    result = contract.execute(_prepared(contract))

    assert result.status is TransferStatus.CONFIRMED
    assert result.external_id == "tx-1"
    assert adapter.calls == 1
    assert journal.get("transfer-1")["status"] == "CONFIRMED"


def test_execute_timeout_persists_unknown_outcome_and_never_retries(tmp_path):
    path = tmp_path / "transfers.json"
    adapter = FakeAdapter(error=TimeoutError("timeout"))
    journal = CapitalTransferJournal(path)
    contract = CapitalTransferContract(
        owner_id="owner",
        adapter=adapter,
        transfer_authorizer=lambda _: True,
        journal=journal,
    )

    result = contract.execute(_prepared(contract))

    assert result.status is TransferStatus.UNKNOWN_OUTCOME
    assert adapter.calls == 1
    assert journal.get("transfer-1")["status"] == "UNKNOWN_OUTCOME"
    assert not contract.can_retry(result)


def test_existing_submitted_identity_blocks_duplicate_adapter_call(tmp_path):
    path = tmp_path / "transfers.json"
    journal = CapitalTransferJournal(path)
    contract = CapitalTransferContract(owner_id="owner")
    record = _prepared(contract)
    journal.reserve(record)
    journal.mark_submitted(
        record.__class__(intent=record.intent, status=TransferStatus.SUBMITTED)
    )

    adapter = FakeAdapter()
    resumed = CapitalTransferContract(
        owner_id="owner",
        adapter=adapter,
        transfer_authorizer=lambda _: True,
        journal=journal,
    )
    result = resumed.execute(record)

    assert result.status is TransferStatus.SUBMITTED
    assert adapter.calls == 0


def test_corrupt_journal_fails_closed(tmp_path):
    path = tmp_path / "transfers.json"
    path.write_text("{not-json", encoding="utf-8")
    journal = CapitalTransferJournal(path)
    contract = CapitalTransferContract(owner_id="owner")
    record = _prepared(contract)
    try:
        journal.reserve(record)
        assert False, "corrupt journal must not be treated as empty"
    except RuntimeError as exc:
        assert "journal" in str(exc)


def test_idempotency_key_collision_is_blocked(tmp_path):
    path = tmp_path / "transfers.json"
    journal = CapitalTransferJournal(path)
    contract = CapitalTransferContract(owner_id="owner")
    first = _prepared(contract)
    journal.reserve(first)
    second = contract.prepare(owner_id="owner", venue_id="other-venue", account_id="account", asset="USDT", amount=10, source="spot", destination="funding", idempotency_key="transfer-1")
    result = journal.reserve(second)
    assert result.status is TransferStatus.BLOCKED
    assert result.reason == "idempotency_key_collision"
