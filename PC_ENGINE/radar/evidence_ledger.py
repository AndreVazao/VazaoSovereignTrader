from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class EvidencePlaneSummary:
    name: str
    status: str
    samples: int
    scenarios: int
    validated_scenarios: int
    mean_net_bps: float
    lower_ci_bps: float
    bootstrap_lower_ci_bps: float
    positive_fold_ratio: float
    folds: int


@dataclass(frozen=True)
class EvidenceLedgerRecord:
    """Immutable, reproducible PAPER evidence audit record."""

    created_at_ms: int
    candidate_id: str
    version: str
    strategy: str
    symbol: str
    regime: str
    horizon_ms: int
    eligible: bool
    reason: str
    reason_codes: tuple[str, ...]
    data_start_ms: int
    data_end_ms: int
    state_count: int
    outcome_count: int
    durable_outcome: EvidencePlaneSummary
    chronological_oos: EvidencePlaneSummary
    source_digest: str

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(payload: dict) -> "EvidenceLedgerRecord":
        durable = EvidencePlaneSummary(**payload["durable_outcome"])
        oos = EvidencePlaneSummary(**payload["chronological_oos"])
        return EvidenceLedgerRecord(
            created_at_ms=int(payload["created_at_ms"]),
            candidate_id=str(payload["candidate_id"]),
            version=str(payload["version"]),
            strategy=str(payload["strategy"]),
            symbol=str(payload["symbol"]),
            regime=str(payload["regime"]),
            horizon_ms=int(payload["horizon_ms"]),
            eligible=bool(payload["eligible"]),
            reason=str(payload["reason"]),
            reason_codes=tuple(str(item) for item in payload.get("reason_codes", ())),
            data_start_ms=int(payload["data_start_ms"]),
            data_end_ms=int(payload["data_end_ms"]),
            state_count=int(payload["state_count"]),
            outcome_count=int(payload["outcome_count"]),
            durable_outcome=durable,
            chronological_oos=oos,
            source_digest=str(payload["source_digest"]),
        )


class EvidenceLedger:
    """Durable append-only PAPER evidence ledger.

    Records are self-contained snapshots. The digest covers all evidence
    fields except the digest itself, allowing later audit to detect mutation
    or accidental mixing of candidate/version/data windows.
    """

    @staticmethod
    def _canonical_payload(record: EvidenceLedgerRecord) -> dict:
        payload = record.to_dict()
        payload.pop("source_digest", None)
        return payload

    @classmethod
    def digest(cls, record: EvidenceLedgerRecord) -> str:
        encoded = json.dumps(
            cls._canonical_payload(record),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @classmethod
    def with_digest(cls, record: EvidenceLedgerRecord) -> EvidenceLedgerRecord:
        return EvidenceLedgerRecord(
            **{
                **record.to_dict(),
                "source_digest": cls.digest(record),
            }
        )

    @staticmethod
    def _validate(record: EvidenceLedgerRecord) -> None:
        if record.created_at_ms <= 0:
            raise ValueError("created_at_ms must be positive")
        if not record.candidate_id.strip() or not record.version.strip():
            raise ValueError("candidate identity must be non-empty")
        if record.horizon_ms <= 0:
            raise ValueError("horizon_ms must be positive")
        if record.data_start_ms <= 0 or record.data_end_ms < record.data_start_ms:
            raise ValueError("invalid evidence data window")
        if record.state_count < 0 or record.outcome_count < 0:
            raise ValueError("evidence counts cannot be negative")
        for plane in (record.durable_outcome, record.chronological_oos):
            if plane.samples < 0 or plane.scenarios < 0 or plane.validated_scenarios < 0:
                raise ValueError("evidence plane counts cannot be negative")
            if plane.validated_scenarios > plane.scenarios:
                raise ValueError("validated scenarios cannot exceed scenarios")
            if not plane.name.strip() or plane.status not in {"PASS", "FAIL", "INCOMPLETE"}:
                raise ValueError("invalid evidence plane status")
        if len(record.source_digest) != 64 or any(
            char not in "0123456789abcdef" for char in record.source_digest
        ):
            raise ValueError("invalid source digest")
        if record.source_digest != EvidenceLedger.digest(record):
            raise ValueError("source digest mismatch")

    @classmethod
    def append(cls, path: str | Path, record: EvidenceLedgerRecord) -> EvidenceLedgerRecord:
        normalized = cls.with_digest(record)
        cls._validate(normalized)
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(normalized.to_dict(), sort_keys=True, separators=(",", ":")) + "\n")
            handle.flush()
        return normalized

    @classmethod
    def load(cls, path: str | Path) -> list[EvidenceLedgerRecord]:
        target = Path(path)
        if not target.exists():
            return []
        records: list[EvidenceLedgerRecord] = []
        for line in target.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = EvidenceLedgerRecord.from_dict(json.loads(line))
            cls._validate(record)
            records.append(record)
        return records

    @staticmethod
    def reason_codes(reason: str) -> tuple[str, ...]:
        if not reason.strip():
            return ()
        return tuple(
            part.strip()
            for part in reason.split(";")
            if part.strip()
        )
