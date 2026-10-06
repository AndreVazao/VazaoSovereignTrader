from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from PC_ENGINE.core.capital_transfer_contract import (
    CapitalTransferRecord,
    TransferStatus,
)


class CapitalTransferJournal:
    """Durable transfer state machine used before any external side effect.

    The journal makes an idempotency key a durable single-flight identity.
    SUBMITTED and UNKNOWN_OUTCOME states survive process restart and cannot be
    converted back to PREPARED, preventing blind duplicate transfers.
    """

    SCHEMA_VERSION = 1

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def _load(self) -> dict[str, dict[str, Any]]:
        if not self.path.exists():
            return {}
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict) or raw.get("schema_version") != self.SCHEMA_VERSION:
                return {}
            records = raw.get("records", {})
            return dict(records) if isinstance(records, dict) else {}
        except (OSError, ValueError, TypeError):
            return {}

    def _save(self, records: dict[str, dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": self.SCHEMA_VERSION,
            "updated_at_ms": int(time.time() * 1000),
            "records": records,
        }
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(
            json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        with tmp.open("r+", encoding="utf-8") as handle:
            handle.flush()
            os.fsync(handle.fileno())
        tmp.replace(self.path)
        try:
            fd = os.open(str(self.path.parent), os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        except OSError:
            pass

    @staticmethod
    def _record_payload(record: CapitalTransferRecord) -> dict[str, Any]:
        return {
            "owner_id": record.intent.owner_id,
            "venue_id": record.intent.venue_id,
            "account_id": record.intent.account_id,
            "asset": record.intent.asset,
            "amount": record.intent.amount,
            "source": record.intent.source,
            "destination": record.intent.destination,
            "idempotency_key": record.intent.idempotency_key,
            "status": record.status.value,
            "external_id": record.external_id,
            "reason": record.reason,
        }

    def reserve(self, record: CapitalTransferRecord) -> CapitalTransferRecord:
        """Persist PREPARED exactly once; existing identity wins."""
        if record.status is not TransferStatus.PREPARED:
            return record
        records = self._load()
        key = record.intent.idempotency_key
        existing = records.get(key)
        if existing:
            status = str(existing.get("status", TransferStatus.UNKNOWN_OUTCOME.value))
            try:
                state = TransferStatus(status)
            except ValueError:
                state = TransferStatus.UNKNOWN_OUTCOME
            return CapitalTransferRecord(
                intent=record.intent,
                status=state,
                external_id=existing.get("external_id"),
                reason=existing.get("reason") or "existing_transfer_identity",
            )
        records[key] = self._record_payload(record)
        self._save(records)
        return record

    def mark_submitted(self, record: CapitalTransferRecord) -> CapitalTransferRecord:
        if record.status is not TransferStatus.SUBMITTED:
            raise ValueError("only SUBMITTED records can be journaled")
        records = self._load()
        key = record.intent.idempotency_key
        existing = records.get(key)
        if existing and str(existing.get("status")) not in {
            TransferStatus.PREPARED.value,
            TransferStatus.SUBMITTED.value,
        }:
            return self._from_existing(record, existing)
        records[key] = self._record_payload(record)
        self._save(records)
        return record

    def resolve(self, record: CapitalTransferRecord) -> CapitalTransferRecord:
        if record.status not in {
            TransferStatus.CONFIRMED,
            TransferStatus.UNKNOWN_OUTCOME,
        }:
            raise ValueError("only terminal transfer outcomes can be resolved")
        records = self._load()
        key = record.intent.idempotency_key
        existing = records.get(key)
        if existing and str(existing.get("status")) == TransferStatus.CONFIRMED.value:
            return self._from_existing(record, existing)
        records[key] = self._record_payload(record)
        self._save(records)
        return record

    def get(self, idempotency_key: str) -> dict[str, Any] | None:
        return self._load().get(str(idempotency_key).strip())

    @staticmethod
    def _from_existing(record: CapitalTransferRecord, existing: dict[str, Any]) -> CapitalTransferRecord:
        try:
            status = TransferStatus(str(existing.get("status")))
        except ValueError:
            status = TransferStatus.UNKNOWN_OUTCOME
        return CapitalTransferRecord(
            intent=record.intent,
            status=status,
            external_id=existing.get("external_id"),
            reason=existing.get("reason") or "existing_transfer_identity",
        )
