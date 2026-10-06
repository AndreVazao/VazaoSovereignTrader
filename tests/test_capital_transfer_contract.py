from __future__ import annotations

from PC_ENGINE.core.capital_transfer_contract import (
    CapitalTransferContract,
    CapitalTransferResult,
    TransferStatus,
)


class FakeAdapter:
    def __init__(self, result: CapitalTransferResult | None = None, error: Exception | None = None):
        self.calls = 0
        self.result = result or CapitalTransferResult(TransferStatus.CONFIRMED, external_id="tx-1")
        self.error = error

    def transfer(self, intent):
        self.calls += 1
        if self.error:
            raise self.error
        return self.result


def _prepared(contract: CapitalTransferContract):
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


def test_transfer_is_blocked_without_explicit_authorizer():
    adapter = FakeAdapter()
    contract = CapitalTransferContract(owner_id="owner", adapter=adapter)

    result = contract.execute(_prepared(contract))

    assert result.status is TransferStatus.BLOCKED
    assert result.reason == "explicit_transfer_authorization_required"
    assert adapter.calls == 0


def test_transfer_is_blocked_when_authorizer_denies():
    adapter = FakeAdapter()
    contract = CapitalTransferContract(
        owner_id="owner",
        adapter=adapter,
        transfer_authorizer=lambda _: False,
    )

    result = contract.execute(_prepared(contract))

    assert result.status is TransferStatus.BLOCKED
    assert result.reason == "transfer_authorization_denied"
    assert adapter.calls == 0


def test_confirmed_transfer_requires_external_id():
    adapter = FakeAdapter(
        CapitalTransferResult(TransferStatus.CONFIRMED, external_id=None)
    )
    contract = CapitalTransferContract(
        owner_id="owner",
        adapter=adapter,
        transfer_authorizer=lambda _: True,
    )

    result = contract.execute(_prepared(contract))

    assert result.status is TransferStatus.UNKNOWN_OUTCOME
    assert adapter.calls == 1
    assert not contract.can_retry(result)


def test_adapter_exception_after_submission_is_unknown_and_not_retryable():
    adapter = FakeAdapter(error=TimeoutError("timeout"))
    contract = CapitalTransferContract(
        owner_id="owner",
        adapter=adapter,
        transfer_authorizer=lambda _: True,
    )

    result = contract.execute(_prepared(contract))

    assert result.status is TransferStatus.UNKNOWN_OUTCOME
    assert "adapter_exception_after_submission" in (result.reason or "")
    assert adapter.calls == 1
    assert not contract.can_retry(result)


def test_unknown_external_outcome_is_not_retryable():
    adapter = FakeAdapter(
        CapitalTransferResult(
            TransferStatus.UNKNOWN_OUTCOME,
            external_id="tx-unknown",
            reason="provider timeout",
        )
    )
    contract = CapitalTransferContract(
        owner_id="owner",
        adapter=adapter,
        transfer_authorizer=lambda _: True,
    )

    result = contract.execute(_prepared(contract))

    assert result.status is TransferStatus.UNKNOWN_OUTCOME
    assert result.external_id == "tx-unknown"
    assert not contract.can_retry(result)


def test_invalid_intent_is_blocked_before_adapter_boundary():
    adapter = FakeAdapter()
    contract = CapitalTransferContract(
        owner_id="owner",
        adapter=adapter,
        transfer_authorizer=lambda _: True,
    )

    record = contract.prepare(
        owner_id="owner",
        venue_id="venue",
        account_id="account",
        asset="USDT",
        amount=0,
        source="spot",
        destination="funding",
        idempotency_key="transfer-1",
    )

    result = contract.execute(record)

    assert result.status is TransferStatus.BLOCKED
    assert result.reason == "transfer_not_in_prepared_state"
    assert adapter.calls == 0


def test_owner_isolation_blocks_transfer():
    adapter = FakeAdapter()
    contract = CapitalTransferContract(
        owner_id="owner",
        adapter=adapter,
        transfer_authorizer=lambda _: True,
    )

    record = contract.prepare(
        owner_id="other-owner",
        venue_id="venue",
        account_id="account",
        asset="USDT",
        amount=10,
        source="spot",
        destination="funding",
        idempotency_key="transfer-1",
    )

    assert record.status is TransferStatus.BLOCKED
    assert adapter.calls == 0
