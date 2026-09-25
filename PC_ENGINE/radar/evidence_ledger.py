from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path


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





@dataclass(frozen=True)
class EvidenceAuditReport:
    """Deterministic aggregate audit over an already verified PAPER ledger."""

    records: int
    eligible_records: int
    rejected_records: int
    eligibility_ratio: float
    candidate_versions: tuple[str, ...]
    symbols: tuple[str, ...]
    regimes: tuple[str, ...]
    strategies: tuple[str, ...]
    reason_counts: tuple[tuple[str, int], ...]
    eligible_by_candidate_version: tuple[tuple[str, int], ...]
    records_by_symbol: tuple[tuple[str, int], ...]
    records_by_regime: tuple[tuple[str, int], ...]
    first_created_at_ms: int | None
    latest_created_at_ms: int | None
    data_start_ms: int | None
    data_end_ms: int | None

@dataclass(frozen=True)
class EvidenceLedgerSummary:
    """Compact historical PAPER evidence report."""

    records: int
    eligible_records: int
    rejected_records: int
    candidate_versions: tuple[str, ...]
    reason_counts: tuple[tuple[str, int], ...]
    latest_created_at_ms: int | None


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
        durable = record.durable_outcome if isinstance(record.durable_outcome, EvidencePlaneSummary) else EvidencePlaneSummary(**record.durable_outcome)
        oos = record.chronological_oos if isinstance(record.chronological_oos, EvidencePlaneSummary) else EvidencePlaneSummary(**record.chronological_oos)
        return EvidenceLedgerRecord(
            created_at_ms=record.created_at_ms,
            candidate_id=record.candidate_id,
            version=record.version,
            strategy=record.strategy,
            symbol=record.symbol,
            regime=record.regime,
            horizon_ms=record.horizon_ms,
            eligible=record.eligible,
            reason=record.reason,
            reason_codes=record.reason_codes,
            data_start_ms=record.data_start_ms,
            data_end_ms=record.data_end_ms,
            state_count=record.state_count,
            outcome_count=record.outcome_count,
            durable_outcome=durable,
            chronological_oos=oos,
            source_digest=cls.digest(record),
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

    @classmethod
    def query(
        cls,
        path: str | Path,
        *,
        candidate_id: str | None = None,
        version: str | None = None,
        symbol: str | None = None,
        regime: str | None = None,
        eligible: bool | None = None,
    ) -> list[EvidenceLedgerRecord]:
        """Load and filter immutable PAPER evidence records.

        Loading always validates every record first, so a query cannot silently
        operate on a tampered ledger.
        """
        records = cls.load(path)
        return [
            record
            for record in records
            if (candidate_id is None or record.candidate_id == candidate_id)
            and (version is None or record.version == version)
            and (symbol is None or record.symbol == symbol)
            and (regime is None or record.regime == regime)
            and (eligible is None or record.eligible is eligible)
        ]

    @classmethod
    def audit_report(cls, records: list[EvidenceLedgerRecord]) -> EvidenceAuditReport:
        """Build deterministic audit aggregates from verified records only."""
        summary = cls.summarize(records)
        candidate_counts: dict[str, int] = {}
        symbol_counts: dict[str, int] = {}
        regime_counts: dict[str, int] = {}
        strategies: set[str] = set()
        first: int | None = None
        latest: int | None = None
        data_start: int | None = None
        data_end: int | None = None

        for record in records:
            key = f"{record.candidate_id}@{record.version}"
            candidate_counts[key] = candidate_counts.get(key, 0) + int(record.eligible)
            symbol_counts[record.symbol] = symbol_counts.get(record.symbol, 0) + 1
            regime_counts[record.regime] = regime_counts.get(record.regime, 0) + 1
            strategies.add(record.strategy)
            first = record.created_at_ms if first is None else min(first, record.created_at_ms)
            latest = record.created_at_ms if latest is None else max(latest, record.created_at_ms)
            data_start = record.data_start_ms if data_start is None else min(data_start, record.data_start_ms)
            data_end = record.data_end_ms if data_end is None else max(data_end, record.data_end_ms)

        ratio = summary.eligible_records / summary.records if summary.records else 0.0
        return EvidenceAuditReport(
            records=summary.records,
            eligible_records=summary.eligible_records,
            rejected_records=summary.rejected_records,
            eligibility_ratio=ratio,
            candidate_versions=summary.candidate_versions,
            symbols=tuple(sorted(symbol_counts)),
            regimes=tuple(sorted(regime_counts)),
            strategies=tuple(sorted(strategies)),
            reason_counts=summary.reason_counts,
            eligible_by_candidate_version=tuple(sorted(candidate_counts.items())),
            records_by_symbol=tuple(sorted(symbol_counts.items())),
            records_by_regime=tuple(sorted(regime_counts.items())),
            first_created_at_ms=first,
            latest_created_at_ms=latest,
            data_start_ms=data_start,
            data_end_ms=data_end,
        )

    @classmethod
    def summarize(cls, records: list[EvidenceLedgerRecord]) -> EvidenceLedgerSummary:
        """Return deterministic aggregate metadata for a verified record set."""
        reason_counts: dict[str, int] = {}
        candidate_versions: set[str] = set()
        latest: int | None = None
        eligible_records = 0

        for record in records:
            candidate_versions.add(f"{record.candidate_id}@{record.version}")
            if record.eligible:
                eligible_records += 1
            latest = record.created_at_ms if latest is None else max(latest, record.created_at_ms)
            for reason_code in record.reason_codes:
                reason_counts[reason_code] = reason_counts.get(reason_code, 0) + 1

        return EvidenceLedgerSummary(
            records=len(records),
            eligible_records=eligible_records,
            rejected_records=len(records) - eligible_records,
            candidate_versions=tuple(sorted(candidate_versions)),
            reason_counts=tuple(sorted(reason_counts.items())),
            latest_created_at_ms=latest,
        )
