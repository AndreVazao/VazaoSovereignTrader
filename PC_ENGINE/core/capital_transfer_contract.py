from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Protocol


class TransferStatus(str, Enum):
    PREPARED = "PREPARED"
    SUBMITTED = "SUBMITTED"
    CONFIRMED = "CONFIRMED"
    UNKNOWN_OUTCOME = "UNKNOWN_OUTCOME"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class CapitalTransferIntent:
    owner_id: str
    venue_id: str
    account_id: str
    asset: str
    amount: float
    source: str
    destination: str
    idempotency_key: str


@dataclass(frozen=True)
class CapitalTransferRecord:
    intent: CapitalTransferIntent
    status: TransferStatus
    external_id: str | None = None
    reason: str | None = None


@dataclass(frozen=True)
class CapitalTransferResult:
    status: TransferStatus
    external_id: str | None = None
    reason: str | None = None


class CapitalTransferAdapter(Protocol):
    def transfer(self, intent: CapitalTransferIntent) -> CapitalTransferResult:
        ...


TransferAuthorizer = Callable[[CapitalTransferIntent], bool]


class CapitalTransferContract:
    """Fail-closed boundary for capital movement.

    This contract deliberately separates authorization from adapter execution.
    No adapter call is possible without an explicit per-transfer authorizer.
    A submitted transfer is never retried automatically: an ambiguous external
    outcome becomes UNKNOWN_OUTCOME and requires reconciliation.
    """

    def __init__(
        self,
        *,
        owner_id: str,
        adapter: CapitalTransferAdapter | None = None,
        transfer_authorizer: TransferAuthorizer | None = None,
    ) -> None:
        self.owner_id = str(owner_id or "").strip().lower()
        self.adapter = adapter
        self.transfer_authorizer = transfer_authorizer
        if not self.owner_id:
            raise ValueError("owner_id is required")

    def prepare(
        self,
        *,
        owner_id: str,
        venue_id: str,
        account_id: str,
        asset: str,
        amount: float,
        source: str,
        destination: str,
        idempotency_key: str,
    ) -> CapitalTransferRecord:
        intent = CapitalTransferIntent(
            owner_id=str(owner_id).strip().lower(),
            venue_id=str(venue_id).strip(),
            account_id=str(account_id).strip(),
            asset=str(asset).upper().strip(),
            amount=float(amount),
            source=str(source).strip(),
            destination=str(destination).strip(),
            idempotency_key=str(idempotency_key).strip(),
        )
        if (
            intent.owner_id != self.owner_id
            or not intent.venue_id
            or not intent.account_id
            or not intent.asset
            or intent.amount <= 0
            or not intent.source
            or not intent.destination
            or not intent.idempotency_key
            or intent.source == intent.destination
        ):
            return CapitalTransferRecord(
                intent=intent,
                status=TransferStatus.BLOCKED,
                reason="invalid_transfer_intent",
            )
        return CapitalTransferRecord(intent=intent, status=TransferStatus.PREPARED)

    def execute(self, record: CapitalTransferRecord) -> CapitalTransferRecord:
        if record.status is not TransferStatus.PREPARED:
            return CapitalTransferRecord(
                intent=record.intent,
                status=TransferStatus.BLOCKED,
                external_id=record.external_id,
                reason="transfer_not_in_prepared_state",
            )
        if record.intent.owner_id != self.owner_id:
            return CapitalTransferRecord(
                intent=record.intent,
                status=TransferStatus.BLOCKED,
                reason="owner_isolation",
            )
        if self.adapter is None:
            return CapitalTransferRecord(
                intent=record.intent,
                status=TransferStatus.BLOCKED,
                reason="transfer_adapter_unavailable",
            )
        if self.transfer_authorizer is None:
            return CapitalTransferRecord(
                intent=record.intent,
                status=TransferStatus.BLOCKED,
                reason="explicit_transfer_authorization_required",
            )
        try:
            authorized = self.transfer_authorizer(record.intent) is True
        except Exception as exc:
            return CapitalTransferRecord(
                intent=record.intent,
                status=TransferStatus.BLOCKED,
                reason=f"authorization_error:{type(exc).__name__}",
            )
        if not authorized:
            return CapitalTransferRecord(
                intent=record.intent,
                status=TransferStatus.BLOCKED,
                reason="transfer_authorization_denied",
            )

        submitted = CapitalTransferRecord(
            intent=record.intent,
            status=TransferStatus.SUBMITTED,
        )
        try:
            result = self.adapter.transfer(submitted.intent)
        except Exception as exc:
            return CapitalTransferRecord(
                intent=submitted.intent,
                status=TransferStatus.UNKNOWN_OUTCOME,
                reason=f"adapter_exception_after_submission:{type(exc).__name__}",
            )

        if result.status is TransferStatus.CONFIRMED and result.external_id:
            return CapitalTransferRecord(
                intent=submitted.intent,
                status=TransferStatus.CONFIRMED,
                external_id=result.external_id,
                reason=result.reason,
            )
        if result.status is TransferStatus.UNKNOWN_OUTCOME:
            return CapitalTransferRecord(
                intent=submitted.intent,
                status=TransferStatus.UNKNOWN_OUTCOME,
                external_id=result.external_id,
                reason=result.reason or "external_outcome_requires_reconciliation",
            )
        return CapitalTransferRecord(
            intent=submitted.intent,
            status=TransferStatus.UNKNOWN_OUTCOME,
            external_id=result.external_id,
            reason=result.reason or "transfer_not_confirmed",
        )

    @staticmethod
    def can_retry(record: CapitalTransferRecord) -> bool:
        # Capital movement must never be blindly retried after submission.
        return record.status is TransferStatus.PREPARED
