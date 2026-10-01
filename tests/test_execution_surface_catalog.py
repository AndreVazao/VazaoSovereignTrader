from __future__ import annotations

from PC_ENGINE.diagnostics.execution_surface_catalog import build_execution_surface_catalog


def test_surface_catalog_is_paper_only_and_not_live_probe() -> None:
    report = build_execution_surface_catalog({
        "browser": {
            "enabled": True,
            "platforms": {
                "demo": {"enabled": True, "surface": "WEB_BROWSER"},
                "android-demo": {"enabled": False, "surface": "ANDROID_APK"},
            },
        }
    })

    assert report["operational_only"] is True
    assert report["paper_only"] is True
    assert report["orders_submitted"] is False
    assert report["execution_authorized"] is False
    assert len(report["venues"]) == 2
    assert report["venues"][0]["live_probe"] is False


def test_surface_catalog_explicitly_marks_unconfigured_browser() -> None:
    report = build_execution_surface_catalog({"browser": {"enabled": False}})

    row = report["venues"][0]
    assert row["state"] == "NOT_CONFIGURED"
    assert row["enabled"] is False


def test_surface_catalog_exposes_truthful_runtime_wiring_audit() -> None:
    report = build_execution_surface_catalog({
        "browser": {
            "enabled": True,
            "platforms": {
                "demo": {"enabled": True, "surface": "WEB_BROWSER"},
            },
        }
    })

    assert report["adapter_runtime_audit"]["observational_only"] is True
    assert report["adapter_runtime_audit"]["implementations"]["WEB_BROWSER"] == "PlaywrightPaperSurfaceAdapter"
    row = report["venues"][0]
    assert row["adapter_implementation"] == "PlaywrightPaperSurfaceAdapter"
    assert row["runtime_wiring"] == "NOT_OBSERVED"
    assert row["library_only"] is True


def test_surface_catalog_marks_runtime_feedback_as_wired(monkeypatch, tmp_path) -> None:
    from PC_ENGINE.diagnostics import execution_surface_catalog as catalog

    class FakeStore:
        def __init__(self, *args, **kwargs):
            pass

        def snapshot(self, stale_after_ms=30_000):
            return {
                "data_write_health": "HEALTHY",
                "surfaces": [{
                    "venue_id": "demo",
                    "surface": "WEB_BROWSER",
                    "state": "HEALTHY",
                    "source": "playwright",
                    "connection_state": "OBSERVED",
                    "last_feedback_age_ms": 100,
                    "reconnects": 0,
                    "detail": "runtime feedback observed",
                }],
            }

    monkeypatch.setattr(catalog, "ExecutionSurfaceFeedbackStore", FakeStore)
    report = build_execution_surface_catalog({
        "browser": {
            "enabled": True,
            "platforms": {
                "demo": {"enabled": True, "surface": "WEB_BROWSER"},
            },
        },
        "execution_surface": {"feedback_path": str(tmp_path / "feedback.jsonl")},
    })

    row = report["venues"][0]
    assert row["runtime_wiring"] == "FEEDBACK_SEEN"
    assert row["library_only"] is False
    assert row["live_probe"] is True
