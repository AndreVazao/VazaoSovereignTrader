from __future__ import annotations

import os
import platform
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .surface_adapters import (
    ActionKind,
    ExecutionSurfaceAdapter,
    Surface,
    SurfaceAction,
    SurfaceFeedback,
    validate_feedback,
)
from .surface_feedback_store import ExecutionSurfaceFeedbackStore


@dataclass(frozen=True)
class DesktopPaperConfig:
    venue_id: str
    executable_path: str
    process_name: str | None = None
    launch_args: tuple[str, ...] = ()
    working_dir: str | None = None
    headless: bool = False
    feedback_path: str | None = None
    feedback_max_records: int = 2_000
    window_title_contains: str | None = None


class DesktopPaperSurfaceAdapter(ExecutionSurfaceAdapter):
    """Windows-first local desktop surface adapter with PAPER-only actions.

    The adapter may launch/observe the installed desktop application, but it
    never clicks order controls, submits forms, invokes private trading APIs,
    or reports a PAPER intent as an exchange fill.
    """

    surface = Surface.DESKTOP_APP

    def __init__(self, config: DesktopPaperConfig) -> None:
        if not config.venue_id:
            raise ValueError("venue_id is required")
        if not config.executable_path:
            raise ValueError("executable_path is required")
        self.config = config
        self._feedback_store = (
            ExecutionSurfaceFeedbackStore(
                config.feedback_path,
                max_records=config.feedback_max_records,
            )
            if config.feedback_path
            else None
        )
        self._process: subprocess.Popen[Any] | None = None

    @staticmethod
    def _now_ms() -> int:
        return int(time.time() * 1000)

    def _feedback(
        self,
        request_id: str,
        *,
        state: str,
        acknowledged: bool,
        detail: str,
        order_reference: str | None = None,
    ) -> SurfaceFeedback:
        feedback = SurfaceFeedback(
            request_id=request_id,
            surface=self.surface,
            venue_id=self.config.venue_id,
            state=state,
            acknowledged=acknowledged,
            observed_at_ms=self._now_ms(),
            detail=detail,
            order_reference=order_reference,
        )
        validate_feedback(feedback)
        if self._feedback_store is not None:
            self._feedback_store.append(feedback)
        return feedback

    def _executable(self) -> Path:
        return Path(self.config.executable_path).expanduser()

    def _process_running_windows(self) -> bool:
        name = self.config.process_name
        if not name:
            return self._process is not None and self._process.poll() is None
        try:
            completed = subprocess.run(
                ["tasklist", "/FI", f"IMAGENAME eq {name}", "/FO", "CSV", "/NH"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return False
        if completed.returncode != 0:
            return False
        expected = name.strip().strip('"').casefold()
        for line in completed.stdout.splitlines():
            image_name = line.split(",", 1)[0].strip().strip('"').casefold()
            if image_name == expected:
                return True
        return False

    def _process_running_posix(self) -> bool:
        name = self.config.process_name
        if not name:
            return self._process is not None and self._process.poll() is None
        try:
            completed = subprocess.run(
                ["pgrep", "-x", name],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return False
        return completed.returncode == 0

    def _process_running(self) -> bool:
        if self._process is not None and self._process.poll() is None:
            return True
        if platform.system() == "Windows":
            return self._process_running_windows()
        return self._process_running_posix()

    def _window_observation(self) -> str:
        title_filter = self.config.window_title_contains
        if not title_filter:
            return "window_title_check=not_configured"
        try:
            from pywinauto import Desktop  # type: ignore
        except ImportError:
            return "window_title_check=pywinauto_not_installed"
        try:
            windows = Desktop(backend="uia").windows(visible_only=True)
            titles = [str(window.window_text()) for window in windows if window.window_text()]
        except Exception as exc:
            return f"window_title_check=error:{type(exc).__name__}"
        matches = [title for title in titles if title_filter.casefold() in title.casefold()]
        # Do not persist raw window titles: they may contain account identifiers
        # or other user-specific data. Record only the match result.
        return f"window_title_match={bool(matches)}"

    def _probe(self, request_id: str) -> SurfaceFeedback:
        executable = self._executable()
        if not executable.is_file():
            return self._feedback(
                request_id,
                state="DOWN",
                acknowledged=False,
                detail=f"executable_not_found:{executable}",
            )
        if not os.access(executable, os.X_OK) and platform.system() != "Windows":
            return self._feedback(
                request_id,
                state="DOWN",
                acknowledged=False,
                detail=f"executable_not_executable:{executable}",
            )
        running = self._process_running()
        if not running:
            return self._feedback(
                request_id,
                state="DISCONNECTED",
                acknowledged=False,
                detail="desktop_application_not_running",
            )
        return self._feedback(
            request_id,
            state="OBSERVED",
            acknowledged=True,
            detail="desktop_application_running;" + self._window_observation(),
        )

    def probe(self) -> SurfaceFeedback:
        return self._probe("desktop-probe")

    def observe(self) -> SurfaceFeedback:
        return self._probe("desktop-observe")

    def _launch(self, request_id: str) -> SurfaceFeedback:
        if self._process is not None and self._process.poll() is None:
            return self._feedback(
                request_id,
                state="CONNECTED",
                acknowledged=True,
                detail="desktop_application_already_running;no_duplicate_launch",
            )
        executable = self._executable()
        if not executable.is_file():
            return self._feedback(
                request_id,
                state="DOWN",
                acknowledged=False,
                detail=f"executable_not_found:{executable}",
            )
        try:
            self._process = subprocess.Popen(
                [str(executable), *self.config.launch_args],
                cwd=self.config.working_dir or None,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                shell=False,
            )
        except (OSError, ValueError) as exc:
            return self._feedback(
                request_id,
                state="DOWN",
                acknowledged=False,
                detail=f"launch_failed:{type(exc).__name__}",
            )
        # Popen only proves process creation was accepted. Detect fast failures.
        time.sleep(0.05)
        exit_code = self._process.poll()
        if exit_code is not None:
            return self._feedback(
                request_id,
                state="DOWN",
                acknowledged=False,
                detail=f"launch_process_exited_immediately:exit_code={exit_code}",
            )
        return self._feedback(
            request_id,
            state="CONNECTED",
            acknowledged=True,
            detail="desktop_application_launched;process_alive_at_observation",
        )

    def execute(self, action: SurfaceAction) -> SurfaceFeedback:
        action = SurfaceAction(
            request_id=action.request_id,
            venue_id=action.venue_id,
            surface=self.surface,
            action=action.action,
            paper_only=True,
        )
        if action.venue_id != self.config.venue_id:
            return self._feedback(
                action.request_id,
                state="REJECTED",
                acknowledged=False,
                detail="venue_id_mismatch",
            )

        if action.action is ActionKind.CONNECT:
            return self._launch(action.request_id)

        if action.action is ActionKind.OBSERVE:
            return self._probe(action.request_id)

        if action.action in {ActionKind.BUY, ActionKind.SELL, ActionKind.CANCEL}:
            return self._feedback(
                action.request_id,
                state="PAPER_INTENT_RECORDED",
                acknowledged=True,
                detail=(
                    f"paper_{action.action.value.lower()}_intent_recorded;"
                    "no_desktop_order_control_clicked;"
                    "no_form_submitted;"
                    "no_private_api_called"
                ),
                order_reference=None,
            )

        return self._feedback(
            action.request_id,
            state="REJECTED",
            acknowledged=False,
            detail="unsupported_action",
        )

    def feedback_snapshot(self) -> dict[str, Any]:
        if self._feedback_store is None:
            return {
                "operational_only": True,
                "paper_only": True,
                "orders_submitted": False,
                "execution_authorized": False,
                "surfaces": [],
            }
        return self._feedback_store.snapshot()
