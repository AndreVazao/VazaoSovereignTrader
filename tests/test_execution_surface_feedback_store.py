import time

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



def test_android_unavailable_state_is_not_reported_healthy(tmp_path):
    from PC_ENGINE.execution.surface_adapters import Surface, SurfaceFeedback

    store = ExecutionSurfaceFeedbackStore(tmp_path / "feedback.jsonl", max_records=10)
    feedback = SurfaceFeedback(
        request_id="adb-down",
        surface=Surface.ANDROID_APK,
        venue_id="android-demo",
        state="ADB_UNAVAILABLE",
        acknowledged=False,
        observed_at_ms=int(time.time() * 1000),
        detail="adb missing",
    )
    assert store.append(feedback)
    row = store.snapshot()["surfaces"][0]
    assert row["state"] == "DOWN"
    assert row["connection_state"] == "ADB_UNAVAILABLE"


def test_android_unconfigured_app_state_is_degraded_not_healthy(tmp_path):
    from PC_ENGINE.execution.surface_adapters import Surface, SurfaceFeedback

    store = ExecutionSurfaceFeedbackStore(tmp_path / "feedback.jsonl", max_records=10)
    feedback = SurfaceFeedback(
        request_id="apk-unconfigured",
        surface=Surface.ANDROID_APK,
        venue_id="android-demo",
        state="APK_NOT_CONFIGURED",
        acknowledged=True,
        observed_at_ms=int(time.time() * 1000),
        detail="package not configured",
    )
    assert store.append(feedback)
    row = store.snapshot()["surfaces"][0]
    assert row["state"] == "DEGRADED"
    assert row["connection_state"] == "APK_NOT_CONFIGURED"


def test_feedback_write_health_survives_new_store_instance(tmp_path, monkeypatch):
    from PC_ENGINE.execution import surface_feedback_store as feedback_module

    path = tmp_path / "feedback.jsonl"
    store = ExecutionSurfaceFeedbackStore(path, max_records=10)
    original_replace = feedback_module.os.replace

    def fail_feedback_replace(src, dst):
        if str(dst) == str(path):
            raise OSError("simulated persistence failure")
        return original_replace(src, dst)

    monkeypatch.setattr(feedback_module.os, "replace", fail_feedback_replace)
    assert store.append(_feedback("CONNECTED", int(time.time() * 1000))) is False

    fresh_store = ExecutionSurfaceFeedbackStore(path, max_records=10)
    report = fresh_store.snapshot()
    assert report["data_write_health"] == "DEGRADED"
    assert report["write_errors"] == 1
    assert "simulated persistence failure" in report["last_write_error"]


def test_feedback_write_health_recovers_after_successful_write(tmp_path, monkeypatch):
    from PC_ENGINE.execution import surface_feedback_store as feedback_module

    path = tmp_path / "feedback.jsonl"
    store = ExecutionSurfaceFeedbackStore(path, max_records=10)
    original_replace = feedback_module.os.replace
    calls = {"failed": False}

    def fail_once(src, dst):
        if str(dst) == str(path) and not calls["failed"]:
            calls["failed"] = True
            raise OSError("simulated transient failure")
        return original_replace(src, dst)

    monkeypatch.setattr(feedback_module.os, "replace", fail_once)
    assert store.append(_feedback("CONNECTED", int(time.time() * 1000))) is False
    assert store.snapshot()["data_write_health"] == "DEGRADED"

    assert store.append(_feedback("OBSERVED", int(time.time() * 1000) + 1)) is True
    report = ExecutionSurfaceFeedbackStore(path, max_records=10).snapshot()
    assert report["data_write_health"] == "HEALTHY"
    assert report["write_errors"] == 0
    assert report["last_write_error"] is None
