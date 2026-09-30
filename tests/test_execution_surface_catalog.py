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
