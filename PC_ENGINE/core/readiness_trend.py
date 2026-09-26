from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class ReadinessTrend:
    status: str
    records: int
    analyzed_records: int
    ready_ratio: float
    baseline_ready_ratio: float
    recent_ready_ratio: float
    improvement_ratio: float
    degradation_ratio: float
    consecutive_ready: int
    consecutive_blocked: int
    first_timestamp_ms: int
    latest_timestamp_ms: int
    span_ms: int
    blockers: tuple[str, ...]
    reason: str

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "records": self.records,
            "analyzed_records": self.analyzed_records,
            "ready_ratio": self.ready_ratio,
            "baseline_ready_ratio": self.baseline_ready_ratio,
            "recent_ready_ratio": self.recent_ready_ratio,
            "improvement_ratio": self.improvement_ratio,
            "degradation_ratio": self.degradation_ratio,
            "consecutive_ready": self.consecutive_ready,
            "consecutive_blocked": self.consecutive_blocked,
            "first_timestamp_ms": self.first_timestamp_ms,
            "latest_timestamp_ms": self.latest_timestamp_ms,
            "span_ms": self.span_ms,
            "blockers": list(self.blockers),
            "reason": self.reason,
        }


class ReadinessTrendEngine:
    """Deterministic, read-only analysis of persisted readiness snapshots."""

    STATUSES = {"STABLE", "DEGRADING", "RECOVERING", "INSUFFICIENT_HISTORY", "INVALID_HISTORY"}

    def __init__(
        self,
        min_samples: int = 10,
        recent_window: int = 5,
        min_span_seconds: int = 300,
        degradation_threshold: float = 0.20,
        recovery_threshold: float = 0.20,
    ):
        self.min_samples = max(1, int(min_samples))
        self.recent_window = max(1, int(recent_window))
        self.min_span_ms = max(0, int(min_span_seconds) * 1000)
        self.degradation_threshold = max(0.0, float(degradation_threshold))
        self.recovery_threshold = max(0.0, float(recovery_threshold))

    @staticmethod
    def _valid_row(row: dict) -> bool:
        if not isinstance(row, dict):
            return False
        try:
            ts = int(row.get("timestamp_ms", 0))
        except (TypeError, ValueError):
            return False
        return ts > 0 and isinstance(row.get("ready"), bool) and isinstance(row.get("blockers", []), list)

    @staticmethod
    def _ratio(rows: list[dict]) -> float:
        return sum(bool(row["ready"]) for row in rows) / len(rows) if rows else 0.0

    @staticmethod
    def _consecutive(rows: list[dict], ready: bool) -> int:
        count = 0
        for row in reversed(rows):
            if bool(row["ready"]) is ready:
                count += 1
            else:
                break
        return count

    def analyze(self, rows: Iterable[dict]) -> ReadinessTrend:
        raw = list(rows)
        if any(not self._valid_row(row) for row in raw):
            return ReadinessTrend(
                "INVALID_HISTORY", len(raw), 0, 0.0, 0.0, 0.0, 0.0, 0.0,
                0, 0, 0, 0, 0, (), "history contains malformed readiness snapshots",
            )
        ordered = sorted(raw, key=lambda row: int(row["timestamp_ms"]))
        if len(ordered) != len({int(row["timestamp_ms"]) for row in ordered}):
            return ReadinessTrend(
                "INVALID_HISTORY", len(raw), 0, 0.0, 0.0, 0.0, 0.0,
                0, 0, 0, 0, 0, 0, (), "history contains duplicate timestamps",
            )
        if len(ordered) < self.min_samples:
            return self._insufficient(len(ordered), ordered, "minimum history samples not reached")
        span_ms = int(ordered[-1]["timestamp_ms"]) - int(ordered[0]["timestamp_ms"])
        if span_ms < self.min_span_ms:
            return self._insufficient(len(ordered), ordered, "minimum history time span not reached")

        window = min(self.recent_window, len(ordered) - 1)
        recent = ordered[-window:]
        baseline = ordered[:-window]
        baseline_ratio = self._ratio(baseline)
        recent_ratio = self._ratio(recent)
        overall_ratio = self._ratio(ordered)
        degradation = max(0.0, baseline_ratio - recent_ratio)
        improvement = max(0.0, recent_ratio - baseline_ratio)
        blocked_streak = self._consecutive(ordered, False)
        ready_streak = self._consecutive(ordered, True)
        blockers = sorted({str(code) for row in recent for code in row.get("blockers", []) if str(code)})

        if degradation >= self.degradation_threshold and recent_ratio < baseline_ratio:
            status, reason = "DEGRADING", "recent readiness ratio declined materially versus baseline"
        elif improvement >= self.recovery_threshold and recent_ratio > baseline_ratio:
            status, reason = "RECOVERING", "recent readiness ratio improved materially versus baseline"
        elif ready_streak >= self.recent_window and recent_ratio == 1.0:
            status, reason = "STABLE", "recent readiness snapshots are continuously ready"
        else:
            status, reason = "STABLE", "no material readiness deterioration or recovery detected"

        return ReadinessTrend(
            status, len(raw), len(ordered), overall_ratio, baseline_ratio, recent_ratio,
            improvement, degradation, ready_streak, blocked_streak,
            int(ordered[0]["timestamp_ms"]), int(ordered[-1]["timestamp_ms"]), span_ms,
            tuple(blockers), reason,
        )

    def _insufficient(self, count: int, ordered: list[dict], reason: str) -> ReadinessTrend:
        first = int(ordered[0]["timestamp_ms"]) if ordered else 0
        latest = int(ordered[-1]["timestamp_ms"]) if ordered else 0
        return ReadinessTrend(
            "INSUFFICIENT_HISTORY", count, len(ordered), self._ratio(ordered),
            self._ratio(ordered), self._ratio(ordered), 0.0, 0.0,
            self._consecutive(ordered, True), self._consecutive(ordered, False),
            first, latest, latest - first, tuple(), reason,
        )
