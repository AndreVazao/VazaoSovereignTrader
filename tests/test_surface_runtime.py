from pathlib import Path

from PC_ENGINE.execution.android_adb_paper_surface import AndroidAdbConfig
from PC_ENGINE.execution.desktop_paper_surface import DesktopPaperConfig
from PC_ENGINE.execution.playwright_paper_surface import PlaywrightPaperConfig
from PC_ENGINE.execution.surface_adapters import Surface
from PC_ENGINE.execution.surface_runtime import ExecutionSurfaceRuntime


def test_instantiate_is_explicit_and_inert(tmp_path: Path) -> None:
    runtime = ExecutionSurfaceRuntime()
    configs = [
        (Surface.WEB_BROWSER, PlaywrightPaperConfig("browser", "https://example.invalid", feedback_path=str(tmp_path / "browser.jsonl"))),
        (Surface.DESKTOP_APP, DesktopPaperConfig("desktop", str(tmp_path / "missing.exe"), feedback_path=str(tmp_path / "desktop.jsonl"))),
        (Surface.ANDROID_APK, AndroidAdbConfig("android", adb_path=str(tmp_path / "missing-adb"), feedback_path=str(tmp_path / "android.jsonl"))),
    ]
    for index, (surface, config) in enumerate(configs):
        record = runtime.instantiate(runtime_id=f"runtime-{index}", surface=surface, config=config)
        assert record.state == "INSTANTIATED"
    snapshot = runtime.snapshot()
    assert snapshot["paper_only"] is True
    assert snapshot["orders_submitted"] is False
    assert snapshot["execution_authorized"] is False
    assert all(item["state"] == "INSTANTIATED" for item in snapshot["adapters"])
    assert not list(tmp_path.glob("*.jsonl"))


def test_probe_is_separate_from_instantiation(tmp_path: Path) -> None:
    runtime = ExecutionSurfaceRuntime()
    config = AndroidAdbConfig("android", adb_path=str(tmp_path / "missing-adb"), feedback_path=str(tmp_path / "feedback.jsonl"))
    runtime.instantiate(runtime_id="android-1", surface=Surface.ANDROID_APK, config=config)
    assert runtime.snapshot()["adapters"][0]["state"] == "INSTANTIATED"
    feedback = runtime.probe("android-1")
    assert feedback.state == "ADB_UNAVAILABLE"
    assert runtime.snapshot()["adapters"][0]["state"] == "PROBED"
    assert (tmp_path / "feedback.jsonl").exists()


def test_close_marks_runtime_closed(tmp_path: Path) -> None:
    runtime = ExecutionSurfaceRuntime()
    config = DesktopPaperConfig("desktop", str(tmp_path / "missing.exe"))
    runtime.instantiate(runtime_id="desktop-1", surface=Surface.DESKTOP_APP, config=config)
    runtime.close("desktop-1")
    assert runtime.snapshot()["adapters"][0]["state"] == "CLOSED"
    assert runtime.get("desktop-1") is None
