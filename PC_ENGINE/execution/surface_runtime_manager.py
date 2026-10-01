from __future__ import annotations

from dataclasses import asdict
from typing import Any

from PC_ENGINE.diagnostics.path_utils import resolve_config_path
from PC_ENGINE.execution.android_adb_paper_surface import AndroidAdbConfig
from PC_ENGINE.execution.desktop_paper_surface import DesktopPaperConfig
from PC_ENGINE.execution.playwright_paper_surface import PlaywrightPaperConfig
from PC_ENGINE.execution.surface_adapters import Surface
from PC_ENGINE.execution.surface_runtime import ExecutionSurfaceRuntime


class ExecutionSurfaceRuntimeManager:
    """Explicit application-owned PAPER runtime lifecycle.

    The manager is created with the application configuration, but it never
    instantiates an adapter during construction. Callers must explicitly ask
    for a runtime instance by runtime_id/venue_id/surface.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.runtime = ExecutionSurfaceRuntime()

    def _surface_config(self, venue_id: str) -> dict[str, Any]:
        execution_cfg = dict(self.config.get('execution_surface', {}))
        configured = execution_cfg.get('platforms')
        if isinstance(configured, dict) and venue_id in configured:
            return dict(configured.get(venue_id) or {})
        browser_cfg = dict(self.config.get('browser', {}))
        platforms = browser_cfg.get('platforms') or {}
        if isinstance(platforms, dict) and venue_id in platforms:
            return dict(platforms.get(venue_id) or {})
        raise ValueError(f'surface configuration not found for venue_id={venue_id}')

    def _feedback_path(self) -> str:
        execution_cfg = dict(self.config.get('execution_surface', {}))
        raw = execution_cfg.get('feedback_path', 'PC_ENGINE/data/execution/surface_feedback.jsonl')
        return str(resolve_config_path(raw))

    def _feedback_max_records(self) -> int:
        execution_cfg = dict(self.config.get('execution_surface', {}))
        return int(execution_cfg.get('feedback_max_records', 2_000))

    def build_adapter_config(self, *, venue_id: str, surface: Surface) -> Any:
        venue_id = str(venue_id or '').strip()
        if not venue_id:
            raise ValueError('venue_id is required')
        raw = self._surface_config(venue_id)
        configured_surface = str(raw.get('surface', '')).strip().upper()
        if configured_surface and configured_surface != surface.value:
            raise ValueError(
                f'surface mismatch for venue_id={venue_id}: configured={configured_surface}, requested={surface.value}'
            )
        feedback_path = str(raw.get('feedback_path') or self._feedback_path())
        max_records = int(raw.get('feedback_max_records', self._feedback_max_records()))

        if surface is Surface.WEB_BROWSER:
            browser_cfg = dict(self.config.get('browser', {}))
            return PlaywrightPaperConfig(
                venue_id=venue_id, url=str(raw.get('url', '')).strip(),
                profile_dir=raw.get('profile_dir', browser_cfg.get('profile_dir')),
                headless=bool(raw.get('headless', browser_cfg.get('headless', True))),
                timeout_ms=int(raw.get('timeout_ms', browser_cfg.get('timeout_ms', 10_000))),
                feedback_path=feedback_path, feedback_max_records=max_records,
            )
        if surface is Surface.DESKTOP_APP:
            launch_args = raw.get('launch_args', ())
            if isinstance(launch_args, list):
                launch_args = tuple(str(item) for item in launch_args)
            elif isinstance(launch_args, tuple):
                launch_args = tuple(str(item) for item in launch_args)
            else:
                raise ValueError('launch_args must be a list or tuple')
            return DesktopPaperConfig(
                venue_id=venue_id, executable_path=str(raw.get('executable_path', '')).strip(),
                process_name=raw.get('process_name'), launch_args=launch_args,
                working_dir=raw.get('working_dir'), headless=bool(raw.get('headless', False)),
                feedback_path=feedback_path, feedback_max_records=max_records,
                window_title_contains=raw.get('window_title_contains'),
            )
        if surface is Surface.ANDROID_APK:
            return AndroidAdbConfig(
                venue_id=venue_id, adb_path=raw.get('adb_path'),
                device_serial=raw.get('device_serial'), package_name=raw.get('package_name'),
                command_timeout_seconds=float(raw.get('command_timeout_seconds', 5.0)),
                feedback_path=feedback_path, feedback_max_records=max_records,
            )
        raise ValueError(f'unsupported runtime surface={surface.value}')

    def instantiate(self, *, runtime_id: str, venue_id: str, surface: Surface) -> dict[str, Any]:
        adapter_config = self.build_adapter_config(venue_id=venue_id, surface=surface)
        record = self.runtime.instantiate(runtime_id=runtime_id, surface=surface, config=adapter_config)
        return asdict(record)

    def probe(self, runtime_id: str) -> dict[str, Any]:
        return asdict(self.runtime.probe(runtime_id))

    def close(self, runtime_id: str) -> dict[str, Any]:
        self.runtime.close(runtime_id)
        return self.runtime.snapshot()

    def runtime_health_stale_after_ms(self) -> int:
        execution_cfg = dict(self.config.get('execution_surface', {}))
        value = execution_cfg.get('runtime_health_stale_after_ms', 30_000)
        value = int(value)
        if value < 0:
            raise ValueError('runtime_health_stale_after_ms must be >= 0')
        return value

    def snapshot(self) -> dict[str, Any]:
        return self.runtime.snapshot(stale_after_ms=self.runtime_health_stale_after_ms())
