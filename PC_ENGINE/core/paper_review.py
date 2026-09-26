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
    def evaluate(base, audit=None, learning=None, champion=None, execution=None):
        audit = audit or {}
        learning = learning or {}
        champion = champion or {}
        execution = execution or {}
        items = (
            ReviewItem("BASE", "PASS" if base.get("ready") else "BLOCKED", str(base.get("status", "missing"))),
            ReviewItem("AUDIT", "PASS" if audit.get("records", 0) > 0 else "INSUFFICIENT_EVIDENCE", f"records={audit.get('records', 0)}"),
            ReviewItem("LEARNING", "BLOCKED" if not learning or learning.get("degradation_detected", False) else "PASS", "learning state"),
            ReviewItem("CHAMPION", "PASS" if champion.get("eligible") else "BLOCKED", str(champion.get("reason", "missing"))),
            ReviewItem("EXECUTION", "PASS" if execution.get("ok") else "BLOCKED", str(execution.get("detail", "missing"))),
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
