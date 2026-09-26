from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class ReadinessScorecardItem:
    name: str
    status: str
    records: int
    pass_count: int
    insufficient_count: int
    blocked_count: int
    pass_ratio: float
    recent_pass_ratio: float
    consecutive_pass: int
    consecutive_blocked: int
    latest_detail: str

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status,
            "records": self.records,
            "pass_count": self.pass_count,
            "insufficient_count": self.insufficient_count,
            "blocked_count": self.blocked_count,
            "pass_ratio": self.pass_ratio,
            "recent_pass_ratio": self.recent_pass_ratio,
            "consecutive_pass": self.consecutive_pass,
            "consecutive_blocked": self.consecutive_blocked,
            "latest_detail": self.latest_detail,
        }


@dataclass(frozen=True)
class ReadinessStabilityScorecard:
    status: str
    records: int
    analyzed_records: int
    recent_window: int
    components: tuple[ReadinessScorecardItem, ...]
    blockers: tuple[str, ...]
    reason: str
    first_timestamp_ms: int
    latest_timestamp_ms: int

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "records": self.records,
            "analyzed_records": self.analyzed_records,
            "recent_window": self.recent_window,
            "components": [item.to_dict() for item in self.components],
            "blockers": list(self.blockers),
            "reason": self.reason,
            "first_timestamp_ms": self.first_timestamp_ms,
            "latest_timestamp_ms": self.latest_timestamp_ms,
            "paper_only": True,
        }


class ReadinessStabilityScorecard:
    """Read-only decomposition of persisted PAPER readiness reviews."""

    COMPONENTS = ("BASE", "AUDIT", "LEARNING", "CHAMPION", "EXECUTION", "READINESS_TREND")
    VALID_STATUSES = {"PASS", "INSUFFICIENT_EVIDENCE", "BLOCKED"}

    def __init__(self, min_samples: int = 10, recent_window: int = 5, min_pass_ratio: float = 1.0):
        self.min_samples = max(1, int(min_samples))
        self.recent_window = max(1, int(recent_window))
        self.min_pass_ratio = min(1.0, max(0.0, float(min_pass_ratio)))

    @classmethod
    def _invalid(cls, count: int, reason: str) -> ReadinessStabilityScorecard:
        return ReadinessStabilityScorecard(
            "INVALID_HISTORY", count, 0, 0, tuple(), tuple(), reason, 0, 0
        )

    @classmethod
    def _valid_row(cls, row: dict) -> bool:
        if not isinstance(row, dict):
            return False
        try:
            ts = int(row.get("timestamp_ms", 0))
        except (TypeError, ValueError):
            return False
        review = row.get("paper_review")
        if ts <= 0 or not isinstance(review, dict) or not isinstance(review.get("items"), list):
            return False
        for item in review["items"]:
            if not isinstance(item, dict):
                return False
            if str(item.get("name", "")) not in cls.COMPONENTS:
                return False
            if str(item.get("status", "")) not in cls.VALID_STATUSES:
                return False
        return True

    @staticmethod
    def _consecutive(statuses: list[str], target: str) -> int:
        count = 0
        for status in reversed(statuses):
            if status == target:
                count += 1
            else:
                break
        return count

    def analyze(self, rows: Iterable[dict]) -> ReadinessStabilityScorecard:
        raw = list(rows)
        if any(not self._valid_row(row) for row in raw):
            return self._invalid(len(raw), "history contains malformed PAPER review snapshots")
        ordered = sorted(raw, key=lambda row: int(row["timestamp_ms"]))
        if len(ordered) != len({int(row["timestamp_ms"]) for row in ordered}):
            return self._invalid(len(raw), "history contains duplicate timestamps")
        if len(ordered) < self.min_samples:
            first = int(ordered[0]["timestamp_ms"]) if ordered else 0
            latest = int(ordered[-1]["timestamp_ms"]) if ordered else 0
            return ReadinessStabilityScorecard(
                "INSUFFICIENT_HISTORY", len(raw), len(ordered), min(self.recent_window, len(ordered)),
                tuple(), tuple(), "minimum scorecard history samples not reached", first, latest
            )

        window = min(self.recent_window, len(ordered))
        recent = ordered[-window:]
        items: list[ReadinessScorecardItem] = []
        blockers: list[str] = []

        for name in self.COMPONENTS:
            statuses = []
            details = []
            for row in ordered:
                found = next((item for item in row["paper_review"]["items"] if str(item.get("name")) == name), None)
                if found is None:
                    return self._invalid(len(raw), f"component {name} missing from a readiness review")
                statuses.append(str(found["status"]))
                details.append(str(found.get("detail", "")))
            recent_statuses = statuses[-window:]
            pass_count = statuses.count("PASS")
            insufficient_count = statuses.count("INSUFFICIENT_EVIDENCE")
            blocked_count = statuses.count("BLOCKED")
            pass_ratio = pass_count / len(statuses)
            recent_pass_ratio = recent_statuses.count("PASS") / len(recent_statuses)
            current = statuses[-1]
            item = ReadinessScorecardItem(
                name=name,
                status=current,
                records=len(statuses),
                pass_count=pass_count,
                insufficient_count=insufficient_count,
                blocked_count=blocked_count,
                pass_ratio=pass_ratio,
                recent_pass_ratio=recent_pass_ratio,
                consecutive_pass=self._consecutive(statuses, "PASS"),
                consecutive_blocked=self._consecutive(statuses, "BLOCKED"),
                latest_detail=details[-1],
            )
            items.append(item)
            if current == "BLOCKED":
                blockers.append(name)

        if blockers:
            status = "BLOCKED"
            reason = "one or more readiness components are currently blocked"
        elif any(item.status == "INSUFFICIENT_EVIDENCE" for item in items):
            status = "INSUFFICIENT_EVIDENCE"
            reason = "one or more readiness components lack sufficient current evidence"
        elif all(item.status == "PASS" and item.recent_pass_ratio >= self.min_pass_ratio for item in items):
            status = "STABLE"
            reason = "all readiness components are passing across the configured recent window"
        else:
            improving = any(
                item.status != "PASS" and item.recent_pass_ratio > item.pass_ratio
                for item in items
            )
            status = "RECOVERING" if improving else "DEGRADING"
            reason = (
                "one or more components are recovering toward sustained readiness"
                if improving else
                "one or more components are not sustaining the required recent pass ratio"
            )

        return ReadinessStabilityScorecard(
            status=status,
            records=len(raw),
            analyzed_records=len(ordered),
            recent_window=window,
            components=tuple(items),
            blockers=tuple(sorted(blockers)),
            reason=reason,
            first_timestamp_ms=int(ordered[0]["timestamp_ms"]),
            latest_timestamp_ms=int(ordered[-1]["timestamp_ms"]),
        )
