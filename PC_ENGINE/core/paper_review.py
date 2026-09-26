from dataclasses import dataclass

@dataclass(frozen=True)
class ReviewItem:
    name: str
    status: str
    detail: str

class PaperReview:
    @staticmethod
    def evaluate(base, audit=None, learning=None, champion=None, execution=None):
        audit = audit or {}
        learning = learning or {}
        champion = champion or {}
        execution = execution or {}
        items = [
            ReviewItem("BASE", "PASS" if base.get("ready") else "BLOCKED", str(base.get("status", "missing"))),
            ReviewItem("AUDIT", "PASS" if audit.get("records", 0) else "INSUFFICIENT_EVIDENCE", "records=%s" % audit.get("records", 0)),
            ReviewItem("LEARNING", "PASS" if learning and not learning.get("degradation_detected", False) else "BLOCKED", "learning state"),
            ReviewItem("CHAMPION", "PASS" if champion.get("eligible") else "BLOCKED", str(champion.get("reason", "missing"))),
            ReviewItem("EXECUTION", "PASS" if execution.get("ok") else "BLOCKED", str(execution.get("detail", "missing"))),
        ]
        blockers = tuple(x.name for x in items if x.status == "BLOCKED")
        missing = tuple(x.name for x in items if x.status == "INSUFFICIENT_EVIDENCE")
        status = "BLOCKED" if blockers else ("INSUFFICIENT_EVIDENCE" if missing else "READY_FOR_REVIEW")
        return {"status": status, "ready": status == "READY_FOR_REVIEW", "items": items, "blockers": blockers, "insufficient": missing}
