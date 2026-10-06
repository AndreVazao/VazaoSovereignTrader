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


class CapitalTransferJournal(Protocol):
    def reserve(self, record: CapitalTransferRecord) -> CapitalTransferRecord:
        ...

    def mark_submitted(self, record: CapitalTransferRecord) -> CapitalTransferRecord:
        ...

    def resolve(self, record: CapitalTransferRecord) -> CapitalTransferRecord:
        ...


TransferAuthorizer = Callable[[CapitalTransferIntent], bool]


class CapitalTransferContract:
    """Fail-closed, durable boundary for capital movement.

    The journal is written before the external side effect. Once SUBMITTED is
    durable, a restart cannot turn the transfer back into a retryable state.
    Ambiguous outcomes require reconciliation rather than another submission.
    """

    def __init__(
        self,
        *,
        owner_id: str,
        adapter: CapitalTransferAdapter | None = None,
        transfer_authorizer: TransferAuthorizer | None = None,
        journal: CapitalTransferJournal | None = None,
    ) -> None:
        self.owner_id = str(owner_id or "").strip().lower()
        self.adapter = adapter
        self.transfer_authorizer = transfer_authorizer
        self.journal = journal
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
            return self._blocked(record, "transfer_not_in_prepared_state")
        if record.intent.owner_id != self.owner_id:
            return self._blocked(record, "owner_isolation")
        if self.journal is not None:
            record = self.journal.reserve(record)
            if record.status is not TransferStatus.PREPARED:
                return record
        if self.adapter is None:
            return self._blocked(record, "transfer_adapter_unavailable")
        if self.transfer_authorizer is None:
            return self._blocked(record, "explicit_transfer_authorization_required")
        try:
            authorized = self.transfer_authorizer(record.intent) is True
        except Exception as exc:
            return self._blocked(record, f"authorization_error:{type(exc).__name__}")
        if not authorized:
            return self._blocked(record, "transfer_authorization_denied")

        submitted = CapitalTransferRecord(intent=record.intent, status=TransferStatus.SUBMITTED)
        if self.journal is not None:
            submitted = self.journal.mark_submitted(submitted)
            if submitted.status is not TransferStatus.SUBMITTED:
                return submitted

        try:
            result = self.adapter.transfer(submitted.intent)
        except Exception as exc:
            return self._resolve(
                CapitalTransferRecord(
                    intent=submitted.intent,
                    status=TransferStatus.UNKNOWN_OUTCOME,
                    reason=f"adapter_exception_after_submission:{type(exc).__name__}",
                )
            )

        if result.status is TransferStatus.CONFIRMED and result.external_id:
            return self._resolve(CapitalTransferRecord(
                intent=submitted.intent,
                status=TransferStatus.CONFIRMED,
                external_id=result.external_id,
                reason=result.reason,
            ))
        return self._resolve(CapitalTransferRecord(
            intent=submitted.intent,
            status=TransferStatus.UNKNOWN_OUTCOME,
            external_id=result.external_id,
            reason=result.reason or "external_outcome_requires_reconciliation",
        ))

    def _resolve(self, record: CapitalTransferRecord) -> CapitalTransferRecord:
        if self.journal is None:
            return record
        return self.journal.resolve(record)

    @staticmethod
    def _blocked(record: CapitalTransferRecord, reason: str) -> CapitalTransferRecord:
        return CapitalTransferRecord(
            intent=record.intent,
            status=TransferStatus.BLOCKED,
            external_id=record.external_id,
            reason=reason,
        )

    @staticmethod
    def can_retry(record: CapitalTransferRecord) -> bool:
        # Only a never-submitted PREPARED identity is retryable.
        return record.status is TransferStatus.PREPARED
