from __future__ import annotations

import json
import math
import time
from dataclasses import asdict, dataclass, field, replace
from enum import Enum
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


class OpportunityStatus(str, Enum):
    DISCOVERED = "DISCOVERED"
    ELIGIBILITY_UNKNOWN = "ELIGIBILITY_UNKNOWN"
    ELIGIBLE_CONFIRMED = "ELIGIBLE_CONFIRMED"
    NET_VALUE_POSITIVE_ESTIMATE = "NET_VALUE_POSITIVE_ESTIMATE"
    PAPER_TESTED = "PAPER_TESTED"
    READY_FOR_EXPLICIT_APPROVAL = "READY_FOR_EXPLICIT_APPROVAL"
    CLAIMED_OR_ENABLED_CONFIRMED = "CLAIMED_OR_ENABLED_CONFIRMED"
    EXPIRED = "EXPIRED"
    BLOCKED = "BLOCKED"
    UNSUPPORTED = "UNSUPPORTED"
    REJECTED_BY_POLICY = "REJECTED_BY_POLICY"
    UNKNOWN_OUTCOME = "UNKNOWN_OUTCOME"


class OpportunityCategory(str, Enum):
    NATIVE_AUTOMATION = "NATIVE_AUTOMATION"
    COPY_TRADING = "COPY_TRADING"
    REWARD_OR_PROMOTION = "REWARD_OR_PROMOTION"
    FEE_REDUCTION = "FEE_REDUCTION"
    RESEARCH_OR_DATA = "RESEARCH_OR_DATA"
    OTHER = "OTHER"


_ALLOWED_TRANSITIONS: dict[OpportunityStatus, set[OpportunityStatus]] = {
    OpportunityStatus.DISCOVERED: {
        OpportunityStatus.ELIGIBILITY_UNKNOWN,
        OpportunityStatus.ELIGIBLE_CONFIRMED,
        OpportunityStatus.BLOCKED,
        OpportunityStatus.UNSUPPORTED,
        OpportunityStatus.EXPIRED,
        OpportunityStatus.REJECTED_BY_POLICY,
    },
    OpportunityStatus.ELIGIBILITY_UNKNOWN: {
        OpportunityStatus.ELIGIBLE_CONFIRMED,
        OpportunityStatus.BLOCKED,
        OpportunityStatus.UNSUPPORTED,
        OpportunityStatus.EXPIRED,
        OpportunityStatus.REJECTED_BY_POLICY,
        OpportunityStatus.UNKNOWN_OUTCOME,
    },
    OpportunityStatus.ELIGIBLE_CONFIRMED: {
        OpportunityStatus.NET_VALUE_POSITIVE_ESTIMATE,
        OpportunityStatus.PAPER_TESTED,
        OpportunityStatus.READY_FOR_EXPLICIT_APPROVAL,
        OpportunityStatus.BLOCKED,
        OpportunityStatus.EXPIRED,
        OpportunityStatus.REJECTED_BY_POLICY,
        OpportunityStatus.UNKNOWN_OUTCOME,
    },
    OpportunityStatus.NET_VALUE_POSITIVE_ESTIMATE: {
        OpportunityStatus.PAPER_TESTED,
        OpportunityStatus.READY_FOR_EXPLICIT_APPROVAL,
        OpportunityStatus.BLOCKED,
        OpportunityStatus.EXPIRED,
        OpportunityStatus.REJECTED_BY_POLICY,
        OpportunityStatus.UNKNOWN_OUTCOME,
    },
    OpportunityStatus.PAPER_TESTED: {
        OpportunityStatus.READY_FOR_EXPLICIT_APPROVAL,
        OpportunityStatus.BLOCKED,
        OpportunityStatus.EXPIRED,
        OpportunityStatus.REJECTED_BY_POLICY,
        OpportunityStatus.UNKNOWN_OUTCOME,
    },
    OpportunityStatus.READY_FOR_EXPLICIT_APPROVAL: {
        OpportunityStatus.PAPER_TESTED,
        OpportunityStatus.CLAIMED_OR_ENABLED_CONFIRMED,
        OpportunityStatus.BLOCKED,
        OpportunityStatus.EXPIRED,
        OpportunityStatus.REJECTED_BY_POLICY,
        OpportunityStatus.UNKNOWN_OUTCOME,
    },
    OpportunityStatus.UNKNOWN_OUTCOME: {
        OpportunityStatus.ELIGIBILITY_UNKNOWN,
        OpportunityStatus.ELIGIBLE_CONFIRMED,
        OpportunityStatus.BLOCKED,
        OpportunityStatus.EXPIRED,
        OpportunityStatus.REJECTED_BY_POLICY,
    },
    OpportunityStatus.CLAIMED_OR_ENABLED_CONFIRMED: {
        OpportunityStatus.EXPIRED,
        OpportunityStatus.BLOCKED,
        OpportunityStatus.UNKNOWN_OUTCOME,
    },
    OpportunityStatus.EXPIRED: set(),
    OpportunityStatus.BLOCKED: set(),
    OpportunityStatus.UNSUPPORTED: set(),
    OpportunityStatus.REJECTED_BY_POLICY: set(),
}


@dataclass(frozen=True)
class OpportunityRecord:
    """Evidence record for a discovered platform opportunity; never an execution command."""

    opportunity_id: str
    venue_id: str
    account_scope: str
    category: OpportunityCategory
    source_url: str
    discovered_at_ms: int
    source_captured_at_ms: int
    status: OpportunityStatus = OpportunityStatus.DISCOVERED
    expires_at_ms: int | None = None
    eligibility_evidence: str = "UNKNOWN"
    gross_value_estimate: float | None = None
    estimated_costs: dict[str, float] = field(default_factory=dict)
    net_value_estimate: float | None = None
    required_permissions: tuple[str, ...] = ()
    risk_notes: tuple[str, ...] = ()
    rationale: str = ""
    updated_at_ms: int = 0
    paper_only: bool = True
    execution_authorized: bool = False

    def validate(self, *, now_ms: int | None = None) -> None:
        now = int(time.time() * 1000) if now_ms is None else int(now_ms)
        for name in ("opportunity_id", "venue_id", "account_scope"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} is required")
        if self.discovered_at_ms <= 0 or self.source_captured_at_ms <= 0:
            raise ValueError("discovery and source-capture timestamps are required")
        if self.source_captured_at_ms > now + 300_000 or self.discovered_at_ms > now + 300_000:
            raise ValueError("timestamps cannot be materially in the future")
        parsed = urlsplit(self.source_url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("source_url must be an HTTPS URL without embedded credentials")
        if self.expires_at_ms is not None and self.expires_at_ms <= 0:
            raise ValueError("expires_at_ms must be positive when supplied")
        for name in ("gross_value_estimate", "net_value_estimate"):
            value = getattr(self, name)
            if value is not None and not math.isfinite(float(value)):
                raise ValueError(f"{name} must be finite")
        for name, value in self.estimated_costs.items():
            if not name.strip() or not math.isfinite(float(value)) or float(value) < 0:
                raise ValueError("cost fields require names and finite non-negative values")
        if self.status == OpportunityStatus.ELIGIBLE_CONFIRMED and self.eligibility_evidence == "UNKNOWN":
            raise ValueError("confirmed eligibility requires evidence")
        if self.status == OpportunityStatus.NET_VALUE_POSITIVE_ESTIMATE:
            if self.net_value_estimate is None or self.net_value_estimate <= 0:
                raise ValueError("positive-net-value status requires a positive estimate")
        if self.execution_authorized:
            raise ValueError("opportunity discovery records cannot authorize execution")
        if not self.paper_only:
            raise ValueError("opportunity records must remain PAPER-only")
        if self.expires_at_ms is not None and self.expires_at_ms <= now and self.status not in {
            OpportunityStatus.EXPIRED,
            OpportunityStatus.BLOCKED,
            OpportunityStatus.UNSUPPORTED,
            OpportunityStatus.REJECTED_BY_POLICY,
        }:
            raise ValueError("expired opportunity must be transitioned to EXPIRED")

    def to_dict(self) -> dict[str, Any]:
        row = asdict(self)
        row["category"] = self.category.value
        row["status"] = self.status.value
        row["required_permissions"] = list(self.required_permissions)
        row["risk_notes"] = list(self.risk_notes)
        return row

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> "OpportunityRecord":
        data = dict(row)
        data["category"] = OpportunityCategory(data["category"])
        data["status"] = OpportunityStatus(data.get("status", OpportunityStatus.DISCOVERED.value))
        data["required_permissions"] = tuple(data.get("required_permissions", ()))
        data["risk_notes"] = tuple(data.get("risk_notes", ()))
        data["estimated_costs"] = dict(data.get("estimated_costs", {}))
        return cls(**data)

    def transition(
        self,
        new_status: OpportunityStatus,
        *,
        now_ms: int | None = None,
        eligibility_evidence: str | None = None,
        net_value_estimate: float | None = None,
        rationale: str | None = None,
    ) -> "OpportunityRecord":
        now = int(time.time() * 1000) if now_ms is None else int(now_ms)
        if new_status == self.status:
            return self
        if new_status not in _ALLOWED_TRANSITIONS[self.status]:
            raise ValueError(f"invalid opportunity status transition: {self.status.value} -> {new_status.value}")
        if self.expires_at_ms is not None and self.expires_at_ms <= now:
            if new_status != OpportunityStatus.EXPIRED:
                raise ValueError("expired opportunities may only transition to EXPIRED")
        updated = replace(
            self,
            status=new_status,
            eligibility_evidence=eligibility_evidence if eligibility_evidence is not None else self.eligibility_evidence,
            net_value_estimate=net_value_estimate if net_value_estimate is not None else self.net_value_estimate,
            rationale=rationale if rationale is not None else self.rationale,
            updated_at_ms=now,
        )
        updated.validate(now_ms=now)
        return updated


class OpportunityRegistry:
    """Append-only local JSONL evidence store; it never executes platform actions."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def list_records(self) -> list[OpportunityRecord]:
        latest: dict[str, OpportunityRecord] = {}
        if not self.path.exists():
            return []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    row = json.loads(line)
                    record = OpportunityRecord.from_dict(row)
                except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                    continue
                latest[record.opportunity_id] = record
        return list(latest.values())

    def upsert(self, record: OpportunityRecord, *, now_ms: int | None = None) -> OpportunityRecord:
        record.validate(now_ms=now_ms)
        current = {item.opportunity_id: item for item in self.list_records()}
        previous = current.get(record.opportunity_id)
        if previous is not None:
            if record.status != previous.status:
                if record.status not in _ALLOWED_TRANSITIONS[previous.status]:
                    raise ValueError("invalid persisted opportunity status transition")
            elif record != previous:
                raise ValueError("same-status updates are not allowed; use transition()")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record.to_dict(), sort_keys=True, allow_nan=False) + "\n")
        return record

    def transition(
        self,
        opportunity_id: str,
        new_status: OpportunityStatus,
        *,
        now_ms: int | None = None,
        eligibility_evidence: str | None = None,
        net_value_estimate: float | None = None,
        rationale: str | None = None,
    ) -> OpportunityRecord:
        records = {item.opportunity_id: item for item in self.list_records()}
        if opportunity_id not in records:
            raise KeyError(opportunity_id)
        updated = records[opportunity_id].transition(
            new_status,
            now_ms=now_ms,
            eligibility_evidence=eligibility_evidence,
            net_value_estimate=net_value_estimate,
            rationale=rationale,
        )
        if updated is not records[opportunity_id]:
            self.upsert(updated, now_ms=now_ms)
        return updated
