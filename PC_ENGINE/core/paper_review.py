from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class ReviewItem:
    name: str
    status: str
    detail: str

    def to_dict(self):
        return asdict(self)


class PaperReview:
    """Deterministic PAPER evidence aggregation; it never authorizes execution."""

    @staticmethod
    def evaluate(base, audit=None, learning=None, champion=None, execution=None, readiness_trend=None):
        audit = audit or {}
        learning = learning or {}
        champion = champion or {}
        execution = execution or {}
        readiness_trend = readiness_trend or {}
        trend_status = str(readiness_trend.get("status", "INSUFFICIENT_HISTORY"))
        trend_recent_ratio = float(readiness_trend.get("recent_ready_ratio", 0.0) or 0.0)
        trend_required_window = max(1, int(readiness_trend.get("required_consecutive_ready", 1) or 1))
        trend_consecutive_ready = int(readiness_trend.get("consecutive_ready", 0) or 0)
        trend_is_stable = (
            trend_status == "STABLE"
            and trend_recent_ratio >= 1.0
            and trend_consecutive_ready >= trend_required_window
        )
        if trend_status == "INSUFFICIENT_HISTORY":
            trend_item = ReviewItem("READINESS_TREND", "INSUFFICIENT_EVIDENCE", str(readiness_trend.get("reason", "insufficient temporal evidence")))
        elif trend_is_stable:
            trend_item = ReviewItem("READINESS_TREND", "PASS", "temporal readiness is stable across the required window")
        else:
            trend_item = ReviewItem("READINESS_TREND", "BLOCKED", f"temporal readiness status={trend_status}; consecutive_ready={trend_consecutive_ready}")
        items = (
            ReviewItem("BASE", "PASS" if base.get("ready") else "BLOCKED", str(base.get("status", "missing"))),
            ReviewItem("AUDIT", "PASS" if audit.get("records", 0) > 0 else "INSUFFICIENT_EVIDENCE", f"records={audit.get('records', 0)}"),
            ReviewItem("LEARNING", "BLOCKED" if not learning or learning.get("degradation_detected", False) else "PASS", "learning state"),
            ReviewItem("CHAMPION", "PASS" if champion.get("eligible") else "BLOCKED", str(champion.get("reason", "missing"))),
            ReviewItem("EXECUTION", "PASS" if execution.get("ok") else "BLOCKED", str(execution.get("detail", "missing"))),
            trend_item,
        )
        blockers = tuple(item.name for item in items if item.status == "BLOCKED")
        insufficient = tuple(item.name for item in items if item.status == "INSUFFICIENT_EVIDENCE")
        status = "BLOCKED" if blockers else ("INSUFFICIENT_EVIDENCE" if insufficient else "READY_FOR_REVIEW")
        return {
            "status": status,
            "ready": status == "READY_FOR_REVIEW",
            "items": [item.to_dict() for item in items],
            "blockers": blockers,
            "insufficient": insufficient,
        }
