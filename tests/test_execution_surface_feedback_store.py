from PC_ENGINE.execution.surface_adapters import SurfaceFeedback
from PC_ENGINE.execution.surface_feedback_store import ExecutionSurfaceFeedbackStore


def _feedback(state: str, ts: int) -> SurfaceFeedback:
    return SurfaceFeedback(
        request_id=f"req-{ts}",
        surface=__import__("PC_ENGINE.execution.surface_adapters", fromlist=["Surface"]).Surface.WEB_BROWSER,
        venue_id="demo",
        state=state,
        acknowledged=state != "DOWN",
        observed_at_ms=ts,
        detail=state,
    )


def test_feedback_store_is_bounded_and_paper_only(tmp_path):
    store = ExecutionSurfaceFeedbackStore(tmp_path / "feedback.jsonl", max_records=2)
    assert store.append(_feedback("CONNECTED", 1000))
    assert store.append(_feedback("OBSERVED", 2000))
    assert store.append(_feedback("OBSERVED", 3000))

    report = store.snapshot(stale_after_ms=10_000)
    assert report["records_retained"] == 2
    assert report["max_records"] == 2
    assert report["data_write_health"] == "HEALTHY"
    assert report["surfaces"][0]["paper_only"] is True
    assert report["surfaces"][0]["execution_authorized"] is False


def test_feedback_store_classifies_stale_and_counts_reconnect(tmp_path):
    store = ExecutionSurfaceFeedbackStore(tmp_path / "feedback.jsonl", max_records=10)
    assert store.append(_feedback("CONNECTED", 1000))
    assert store.append(_feedback("DOWN", 2000))
    assert store.append(_feedback("CONNECTED", 3000))

    report = store.snapshot(stale_after_ms=500)
    row = report["surfaces"][0]
    assert row["state"] == "DEGRADED"
    assert row["connection_state"] == "CONNECTED"
    assert row["last_feedback_age_ms"] is not None
    assert row["reconnects"] == 1
