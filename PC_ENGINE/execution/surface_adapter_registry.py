from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Type

from .android_adb_paper_surface import AndroidAdbPaperSurfaceAdapter
from .desktop_paper_surface import DesktopPaperSurfaceAdapter
from .playwright_paper_surface import PlaywrightPaperSurfaceAdapter
from .surface_adapters import ExecutionSurfaceAdapter, Surface


@dataclass(frozen=True)
class AdapterRegistration:
    surface: Surface
    implementation: Type[ExecutionSurfaceAdapter]
    paper_only: bool = True


_REGISTRATIONS: dict[Surface, AdapterRegistration] = {
    Surface.WEB_BROWSER: AdapterRegistration(
        Surface.WEB_BROWSER, PlaywrightPaperSurfaceAdapter
    ),
    Surface.DESKTOP_APP: AdapterRegistration(
        Surface.DESKTOP_APP, DesktopPaperSurfaceAdapter
    ),
    Surface.ANDROID_APK: AdapterRegistration(
        Surface.ANDROID_APK, AndroidAdbPaperSurfaceAdapter
    ),
}


def get_adapter_registration(surface: Surface) -> AdapterRegistration | None:
    return _REGISTRATIONS.get(surface)


def adapter_registrations() -> dict[str, dict[str, Any]]:
    return {
        surface.value: {
            "implementation": registration.implementation.__name__,
            "registered": True,
            "paper_only": registration.paper_only,
            "instantiated": False,
        }
        for surface, registration in _REGISTRATIONS.items()
    }


def instantiate_adapter(surface: Surface, config: Any) -> ExecutionSurfaceAdapter:
    registration = get_adapter_registration(surface)
    if registration is None:
        raise ValueError(f"no adapter registered for surface={surface.value}")
    adapter = registration.implementation(config)
    if not getattr(adapter, "surface", None) is surface:
        raise RuntimeError(
            f"adapter surface mismatch: expected={surface.value}"
        )
    return adapter
