from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

from PC_ENGINE.radar.evidence_ledger import EvidenceAuditReport, EvidenceLedgerRecord


@dataclass(frozen=True)
class LearningAction:
    candidate_version: str
    symbol: str
    regime: str
    action: str
    reason: str
    records: int
    eligible_records: int
    eligibility_ratio: float


@dataclass(frozen=True)
class PaperEvidenceLearningSnapshot:
    """Deterministic PAPER-only learning guidance from verified evidence.

    This is descriptive/advisory state. It never promotes a candidate, changes
    risk, authorizes capital, or executes an order.
    """

    records: int
    eligible_records: int
    rejected_records: int
    eligibility_ratio: float
    recent_records: int
    recent_eligible_records: int
    recent_eligibility_ratio: float
    historical_eligibility_ratio: float
    degradation_detected: bool
    actions: tuple[LearningAction, ...]
    audit: EvidenceAuditReport

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["audit"] = asdict(self.audit)
        payload["actions"] = [asdict(action) for action in self.actions]
        return payload


class PaperEvidenceLearningLoop:
    """Turn the verified evidence ledger into bounded learning observations."""

    def __init__(self, *, recent_records: int = 20, degradation_threshold: float = 0.20) -> None:
        self.recent_records = max(1, int(recent_records))
        self.degradation_threshold = max(0.0, min(1.0, float(degradation_threshold)))

    @staticmethod
    def _ratio(records: list[EvidenceLedgerRecord]) -> float:
        return (
            sum(1 for record in records if record.eligible) / len(records)
            if records
            else 0.0
        )

    def evaluate(
        self,
        records: Iterable[EvidenceLedgerRecord],
        *,
        audit: EvidenceAuditReport | None = None,
    ) -> PaperEvidenceLearningSnapshot:
        ordered = sorted(
            list(records),
            key=lambda record: (record.created_at_ms, record.candidate_id, record.version, record.symbol, record.regime),
        )
        if audit is None:
            from PC_ENGINE.radar.evidence_ledger import EvidenceLedger
            audit = EvidenceLedger.audit_report(ordered)

        recent = ordered[-self.recent_records :]
        historical = ordered[:-len(recent)] if len(ordered) > len(recent) else []
        recent_ratio = self._ratio(recent)
        historical_ratio = self._ratio(historical)
        degradation = bool(
            historical
            and historical_ratio - recent_ratio >= self.degradation_threshold
        )

        grouped: dict[tuple[str, str, str], list[EvidenceLedgerRecord]] = {}
        for record in ordered:
            key = (f"{record.candidate_id}@{record.version}", record.symbol, record.regime)
            grouped.setdefault(key, []).append(record)

        actions: list[LearningAction] = []
        for (candidate_version, symbol, regime), rows in sorted(grouped.items()):
            ratio = self._ratio(rows)
            latest = rows[-1]
            if len(rows) < 2:
                action = "OBSERVE"
                reason = "insufficient temporal history for degradation check"
            else:
                prior_ratio = self._ratio(rows[:-1])
                if prior_ratio - ratio >= self.degradation_threshold:
                    action = "INVESTIGATE"
                    reason = "candidate/symbol/regime eligibility degraded in latest observation"
                elif not latest.eligible:
                    action = "OBSERVE"
                    reason = "latest evidence record is not eligible"
                else:
                    action = "RETAIN"
                    reason = "latest evidence remains eligible without detected degradation"
            actions.append(
                LearningAction(
                    candidate_version=candidate_version,
                    symbol=symbol,
                    regime=regime,
                    action=action,
                    reason=reason,
                    records=len(rows),
                    eligible_records=sum(1 for row in rows if row.eligible),
                    eligibility_ratio=ratio,
                )
            )

        return PaperEvidenceLearningSnapshot(
            records=audit.records,
            eligible_records=audit.eligible_records,
            rejected_records=audit.rejected_records,
            eligibility_ratio=audit.eligibility_ratio,
            recent_records=len(recent),
            recent_eligible_records=sum(1 for record in recent if record.eligible),
            recent_eligibility_ratio=recent_ratio,
            historical_eligibility_ratio=historical_ratio,
            degradation_detected=degradation,
            actions=tuple(actions),
            audit=audit,
        )
