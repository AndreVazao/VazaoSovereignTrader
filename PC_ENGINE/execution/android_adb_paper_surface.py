from __future__ import annotations

import shutil
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
class AndroidAdbConfig:
    """Configuration for read-only Android device/emulator observation."""

    venue_id: str
    adb_path: str | None = None
    device_serial: str | None = None
    package_name: str | None = None
    command_timeout_seconds: float = 5.0
    feedback_path: str | None = None
    feedback_max_records: int = 2_000


class AndroidAdbPaperSurfaceAdapter(ExecutionSurfaceAdapter):
    """Read-only ADB bridge with PAPER-only action feedback."""

    surface = Surface.ANDROID_APK

    def __init__(self, config: AndroidAdbConfig) -> None:
        if not config.venue_id:
            raise ValueError("venue_id is required")
        if config.command_timeout_seconds <= 0:
            raise ValueError("command_timeout_seconds must be positive")
        if config.feedback_max_records < 1:
            raise ValueError("feedback_max_records must be positive")
        self.config = config
        self._feedback_store = (
            ExecutionSurfaceFeedbackStore(config.feedback_path, max_records=config.feedback_max_records)
            if config.feedback_path else None
        )

    @staticmethod
    def _now_ms() -> int:
        return int(time.time() * 1000)

    def _feedback(self, request_id: str, *, state: str, acknowledged: bool, detail: str) -> SurfaceFeedback:
        feedback = SurfaceFeedback(
            request_id=request_id, surface=self.surface, venue_id=self.config.venue_id,
            state=state, acknowledged=acknowledged, observed_at_ms=self._now_ms(),
            detail=detail, order_reference=None,
        )
        validate_feedback(feedback)
        if self._feedback_store is not None:
            self._feedback_store.append(feedback)
        return feedback

    def _resolve_adb(self) -> str | None:
        if self.config.adb_path:
            path = Path(self.config.adb_path).expanduser()
            return str(path) if path.is_file() else None
        return shutil.which("adb")

    def _run(self, command: list[str]) -> tuple[str, str, int | None, str | None]:
        try:
            completed = subprocess.run(
                command, capture_output=True, text=True,
                timeout=self.config.command_timeout_seconds, check=False, shell=False,
            )
        except subprocess.TimeoutExpired:
            return "", "", None, "TIMEOUT"
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            return "", "", None, f"ERROR:{type(exc).__name__}"
        return completed.stdout or "", completed.stderr or "", completed.returncode, None

    @staticmethod
    def _parse_devices(output: str) -> tuple[list[tuple[str, str]], bool]:
        lines = output.splitlines()
        header_index = next(
            (i for i, line in enumerate(lines) if line.strip().startswith("List of devices attached")),
            None,
        )
        if header_index is None:
            return [], False

        devices: list[tuple[str, str]] = []
        malformed = False
        allowed = {
            "device", "offline", "unauthorized", "authorizing", "no permissions",
            "recovery", "sideload", "bootloader", "connecting",
        }
        for line in lines[header_index + 1:]:
            stripped = line.strip()
            if not stripped:
                continue
            parts = stripped.split()
            if len(parts) < 2:
                malformed = True
                continue
            serial = parts[0]
            # ADB may emit a multi-word state such as "no permissions".
            state = "no permissions" if len(parts) >= 3 and parts[1].lower() == "no" and parts[2].lower() == "permissions" else parts[1].lower()
            if state not in allowed:
                malformed = True
                continue
            devices.append((serial, state))
        return devices, not malformed

    def _observe(self, request_id: str) -> SurfaceFeedback:
        adb = self._resolve_adb()
        if not adb:
            return self._feedback(request_id, state="ADB_UNAVAILABLE", acknowledged=False, detail="adb_executable_unavailable_or_invalid")

        _, _, version_code, version_error = self._run([adb, "version"])
        if version_error == "TIMEOUT":
            return self._feedback(request_id, state="COMMUNICATION_ERROR", acknowledged=False, detail="adb_version_timeout")
        if version_error:
            return self._feedback(request_id, state="COMMUNICATION_ERROR", acknowledged=False, detail=f"adb_version_{version_error.lower()}")
        if version_code != 0:
            return self._feedback(request_id, state="ADB_UNAVAILABLE", acknowledged=False, detail=f"adb_version_exit_code={version_code}")

        stdout, _, return_code, error = self._run([adb, "devices", "-l"])
        if error == "TIMEOUT":
            return self._feedback(request_id, state="COMMUNICATION_ERROR", acknowledged=False, detail="adb_devices_timeout")
        if error:
            return self._feedback(request_id, state="COMMUNICATION_ERROR", acknowledged=False, detail=f"adb_devices_{error.lower()}")
        if return_code != 0:
            return self._feedback(request_id, state="COMMUNICATION_ERROR", acknowledged=False, detail=f"adb_devices_exit_code={return_code}")

        devices, well_formed = self._parse_devices(stdout)
        if not well_formed:
            return self._feedback(request_id, state="COMMUNICATION_ERROR", acknowledged=False, detail="adb_devices_malformed_output")

        if self.config.device_serial:
            devices = [item for item in devices if item[0] == self.config.device_serial]
            if not devices:
                return self._feedback(request_id, state="NO_DEVICE", acknowledged=False, detail="configured_device_not_present")
        if not devices:
            return self._feedback(request_id, state="NO_DEVICE", acknowledged=False, detail="no_android_device_or_emulator_connected")

        online = [item for item in devices if item[1] == "device"]
        if not online:
            states = {state for _, state in devices}
            if states.intersection({"unauthorized", "authorizing", "no permissions"}):
                return self._feedback(request_id, state="DEVICE_UNAUTHORIZED", acknowledged=False, detail="device_requires_local_adb_authorization_or_permissions")
            if "offline" in states:
                return self._feedback(request_id, state="DEVICE_OFFLINE", acknowledged=False, detail="adb_device_offline")
            return self._feedback(request_id, state="COMMUNICATION_ERROR", acknowledged=False, detail="no_usable_adb_device_state")

        if len(online) > 1 and not self.config.device_serial:
            return self._feedback(
                request_id, state="MULTIPLE_DEVICES", acknowledged=True,
                detail=f"multiple_online_devices:{len(online)};configure_device_serial_to_select_one",
            )
        if not self.config.package_name:
            return self._feedback(
                request_id, state="APK_NOT_CONFIGURED", acknowledged=True,
                detail="adb_device_connected;package_name_not_configured;app_state_not_checked",
            )

        serial = online[0][0]
        package = self.config.package_name.strip()
        if not package or any(char.isspace() for char in package):
            return self._feedback(request_id, state="COMMUNICATION_ERROR", acknowledged=False, detail="configured_package_name_invalid")

        stdout, _, return_code, error = self._run([adb, "-s", serial, "shell", "pidof", package])
        if error == "TIMEOUT":
            return self._feedback(request_id, state="COMMUNICATION_ERROR", acknowledged=False, detail="app_process_observation_timeout")
        if error:
            return self._feedback(request_id, state="COMMUNICATION_ERROR", acknowledged=False, detail=f"app_process_observation_{error.lower()}")
        if return_code == 0 and stdout.strip():
            return self._feedback(request_id, state="APP_OBSERVED", acknowledged=True, detail="adb_device_connected;configured_package_process_observed")
        if return_code in {0, 1}:
            return self._feedback(request_id, state="APP_NOT_OBSERVED", acknowledged=False, detail="adb_device_connected;configured_package_process_not_observed")
        return self._feedback(request_id, state="COMMUNICATION_ERROR", acknowledged=False, detail=f"app_process_observation_exit_code={return_code}")

    def probe(self) -> SurfaceFeedback:
        return self._observe("android-adb-probe")

    def observe(self) -> SurfaceFeedback:
        return self._observe("android-adb-observe")

    def execute(self, action: SurfaceAction) -> SurfaceFeedback:
        if action.venue_id != self.config.venue_id:
            return self._feedback(action.request_id, state="REJECTED", acknowledged=False, detail="venue_id_mismatch")
        if action.action in {ActionKind.CONNECT, ActionKind.OBSERVE}:
            # CONNECT is intentionally read-only: no APK install or launch.
            return self._observe(action.request_id)
        if action.action in {ActionKind.BUY, ActionKind.SELL, ActionKind.CANCEL}:
            return self._feedback(
                action.request_id, state="PAPER_INTENT_RECORDED", acknowledged=True,
                detail=(
                    f"paper_{action.action.value.lower()}_intent_recorded;"
                    "no_android_ui_interaction;no_apk_install_or_launch;"
                    "no_order_submitted;no_private_api_called"
                ),
            )
        return self._feedback(action.request_id, state="REJECTED", acknowledged=False, detail="unsupported_action")

    def feedback_snapshot(self) -> dict[str, Any]:
        if self._feedback_store is None:
            return {"operational_only": True, "paper_only": True, "orders_submitted": False, "execution_authorized": False, "surfaces": []}
        return self._feedback_store.snapshot()
