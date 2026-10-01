from PC_ENGINE.execution.android_adb_paper_surface import AndroidAdbConfig
from PC_ENGINE.execution.desktop_paper_surface import DesktopPaperConfig
from PC_ENGINE.execution.playwright_paper_surface import PlaywrightPaperConfig
from PC_ENGINE.execution.surface_adapter_registry import (
    adapter_registrations,
    instantiate_adapter,
)
from PC_ENGINE.execution.surface_adapters import Surface


def test_all_supported_paper_surfaces_are_registered() -> None:
    registrations = adapter_registrations()

    assert set(registrations) == {
        Surface.WEB_BROWSER.value,
        Surface.DESKTOP_APP.value,
        Surface.ANDROID_APK.value,
    }
    assert all(item["registered"] is True for item in registrations.values())
    assert all(item["paper_only"] is True for item in registrations.values())
    assert all(item["instantiated"] is False for item in registrations.values())


def test_registry_can_instantiate_without_starting_transport(tmp_path) -> None:
    configs = {
        Surface.WEB_BROWSER: PlaywrightPaperConfig(
            venue_id="browser-demo",
            url="https://example.invalid",
            feedback_path=str(tmp_path / "browser.jsonl"),
        ),
        Surface.DESKTOP_APP: DesktopPaperConfig(
            venue_id="desktop-demo",
            executable_path="/nonexistent/trading-app.exe",
            feedback_path=str(tmp_path / "desktop.jsonl"),
        ),
        Surface.ANDROID_APK: AndroidAdbConfig(
            venue_id="android-demo",
            adb_path="/nonexistent/adb",
            feedback_path=str(tmp_path / "android.jsonl"),
        ),
    }

    adapters = {
        surface: instantiate_adapter(surface, config)
        for surface, config in configs.items()
    }

    assert all(adapter.surface is surface for surface, adapter in adapters.items())
    assert not any(
        (tmp_path / name).exists()
        for name in ("browser.jsonl", "desktop.jsonl", "android.jsonl")
    )
