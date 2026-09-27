from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class ReadinessTimelineEvent:
    timestamp_ms: int
    component: str
    from_status: str
    to_status: str
    direction: str
    detail: str
    previous_timestamp_ms: int
    duration_ms: int

    def to_dict(self) -> dict:
        return {
            "timestamp_ms": self.timestamp_ms,
            "component": self.component,
            "from_status": self.from_status,
            "to_status": self.to_status,
            "direction": self.direction,
            "detail": self.detail,
            "previous_timestamp_ms": self.previous_timestamp_ms,
            "duration_ms": self.duration_ms,
        }


@dataclass(frozen=True)
class ReadinessDiagnosticTimelineReport:
    status: str
    records: int
    analyzed_records: int
    events: tuple[ReadinessTimelineEvent, ...]
    components: tuple[str, ...]
    first_timestamp_ms: int
    latest_timestamp_ms: int
    reason: str

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "records": self.records,
            "analyzed_records": self.analyzed_records,
            "events": [event.to_dict() for event in self.events],
            "components": list(self.components),
            "first_timestamp_ms": self.first_timestamp_ms,
            "latest_timestamp_ms": self.latest_timestamp_ms,
            "reason": self.reason,
            "paper_only": True,
        }


class ReadinessDiagnosticTimeline:
    """Deterministic, read-only transition timeline for persisted PAPER readiness."""

    COMPONENTS = ("BASE", "AUDIT", "LEARNING", "CHAMPION", "EXECUTION", "READINESS_TREND")
    VALID_STATUSES = {"PASS", "INSUFFICIENT_EVIDENCE", "BLOCKED"}

    def __init__(self, max_events: int = 200):
        self.max_events = max(1, int(max_events))

    @classmethod
    def _valid_row(cls, row: dict) -> bool:
        if not isinstance(row, dict):
            return False
        try:
            timestamp = int(row.get("timestamp_ms", 0))
        except (TypeError, ValueError):
            return False
        if timestamp <= 0:
            return False
        review = row.get("paper_review")
        if not isinstance(review, dict) or not isinstance(review.get("items"), list):
            return False
        names = set()
        for item in review["items"]:
            if not isinstance(item, dict):
                return False
            name = str(item.get("name", ""))
            status = str(item.get("status", ""))
            if name not in cls.COMPONENTS or status not in cls.VALID_STATUSES or name in names:
                return False
            names.add(name)
        return names == set(cls.COMPONENTS)

    @staticmethod
    def _direction(previous: str, current: str) -> str:
        if previous == current:
            return "STABLE"
        if current == "PASS":
            return "RECOVERING"
        if current == "BLOCKED":
            return "DEGRADING"
        return "CHANGING"

    def analyze(self, rows: Iterable[dict]) -> ReadinessDiagnosticTimelineReport:
        raw = list(rows)
        if any(not self._valid_row(row) for row in raw):
            return ReadinessDiagnosticTimelineReport(
                "INVALID_HISTORY", len(raw), 0, tuple(), tuple(), 0, 0,
                "history contains malformed PAPER readiness snapshots",
            )
        ordered = sorted(raw, key=lambda row: int(row["timestamp_ms"]))
        timestamps = [int(row["timestamp_ms"]) for row in ordered]
        if len(timestamps) != len(set(timestamps)):
            return ReadinessDiagnosticTimelineReport(
                "INVALID_HISTORY", len(raw), 0, tuple(), tuple(), 0, 0,
                "history contains duplicate timestamps",
            )
        if not ordered:
            return ReadinessDiagnosticTimelineReport(
                "INSUFFICIENT_HISTORY", 0, 0, tuple(), tuple(self.COMPONENTS), 0, 0,
                "no readiness history available",
            )

        previous: dict[str, tuple[str, int, str]] = {}
        events: list[ReadinessTimelineEvent] = []
        for row in ordered:
            timestamp = int(row["timestamp_ms"])
            items = {str(item["name"]): item for item in row["paper_review"]["items"]}
            for component in self.COMPONENTS:
                item = items[component]
                current = str(item["status"])
                detail = str(item.get("detail", ""))
                prior = previous.get(component)
                if prior is not None and prior[0] != current:
                    previous_status, previous_timestamp, _ = prior
                    events.append(
                        ReadinessTimelineEvent(
                            timestamp_ms=timestamp,
                            component=component,
                            from_status=previous_status,
                            to_status=current,
                            direction=self._direction(previous_status, current),
                            detail=detail,
                            previous_timestamp_ms=previous_timestamp,
                            duration_ms=max(0, timestamp - previous_timestamp),
                        )
                    )
                previous[component] = (current, timestamp, detail)

        events.sort(key=lambda event: (event.timestamp_ms, event.component, event.to_status))
        events = events[-self.max_events:]
        return ReadinessDiagnosticTimelineReport(
            "STABLE" if not events else "TRANSITIONS",
            len(raw),
            len(ordered),
            tuple(events),
            tuple(self.COMPONENTS),
            timestamps[0],
            timestamps[-1],
            "no component status transitions detected" if not events else "chronological readiness component transitions detected",
        )

    def query(
        self,
        rows: Iterable[dict],
        component: str | None = None,
        direction: str | None = None,
        from_status: str | None = None,
        to_status: str | None = None,
        limit: int | None = None,
    ) -> dict:
        result = self.analyze(rows)
        events = list(result.events)
        if component is not None:
            component = str(component).upper()
            events = [event for event in events if event.component == component]
        if direction is not None:
            direction = str(direction).upper()
            events = [event for event in events if event.direction == direction]
        if from_status is not None:
            from_status = str(from_status).upper()
            events = [event for event in events if event.from_status == from_status]
        if to_status is not None:
            to_status = str(to_status).upper()
            events = [event for event in events if event.to_status == to_status]
        if limit is not None:
            events = events[-max(1, int(limit)):]
        payload = result.to_dict()
        payload["events"] = [event.to_dict() for event in events]
        payload["filters"] = {
            "component": component,
            "direction": direction,
            "from_status": from_status,
            "to_status": to_status,
            "limit": limit,
        }
        payload["returned_events"] = len(events)
        return payload
