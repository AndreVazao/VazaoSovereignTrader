from __future__ import annotations

"""Parent-side Linux launcher for the strict manifest-backed connector sandbox.

This adapter is deliberately not wired into ConnectorRegistry yet. A caller must
supply an explicit package runtime manifest and trusted factory reference. Any
missing Bubblewrap support, invalid manifest or process failure is a hard denial;
there is no multiprocessing or unsandboxed fallback.
"""

import json
import os
import re
import selectors
import signal
import subprocess
import sys
import time
from collections.abc import Mapping
from typing import Any

from PC_ENGINE.core.connector_runtime_manifest import RuntimeManifest
from PC_ENGINE.core.connector_worker_limits import validate_worker_limits
from PC_ENGINE.core.connector_worker_sandbox import (
    SandboxUnavailable,
    build_linux_bwrap_command,
)


class LinuxSandboxLaunchError(RuntimeError):
    """Sanitized failure from the manifest-backed Linux worker launcher."""


class LinuxBubblewrapConnectorAdapter:
    """Execute one connector read inside a fresh, network-denied Bubblewrap sandbox.

    The trusted parent owns the process and IPC pipes. The worker receives only
    a bounded JSON request on stdin and returns one bounded JSON envelope on
    stdout. stderr is discarded to prevent provider output leaking into logs.
    The runtime manifest is revalidated by the command builder immediately
    before launch. This class does not authenticate the manifest or close the
    filesystem validation-to-mount race; callers must keep package files
    root-owned and immutable. It is not yet a production registry integration.
    """

    def __init__(
        self,
        factory_reference: str,
        *,
        runtime_manifest: RuntimeManifest,
        python_home: str,
        runtime_library_path: str | None = None,
        bwrap_path: str | None = None,
        memory_limit_mb: int = 256,
        cpu_time_limit_seconds: int = 20,
        max_request_bytes: int = 32_768,
        max_response_bytes: int = 262_144,
    ) -> None:
        if not isinstance(factory_reference, str) or not factory_reference:
            raise ValueError("factory_reference_required")
        if not isinstance(runtime_manifest, RuntimeManifest):
            raise ValueError("runtime_manifest_required")
        if not isinstance(python_home, str) or not python_home.startswith("/"):
            raise ValueError("python_home_must_be_absolute")
        if not 1 <= max_request_bytes <= 32_768:
            raise ValueError("invalid_request_limit")
        if not 1 <= max_response_bytes <= 262_144:
            raise ValueError("invalid_response_limit")
        validate_worker_limits(memory_limit_mb, cpu_time_limit_seconds)
        self._factory_reference = factory_reference
        self._runtime_manifest = runtime_manifest
        self._python_home = python_home
        self._runtime_library_path = runtime_library_path
        self._bwrap_path = bwrap_path
        self._memory_limit_mb = memory_limit_mb
        self._cpu_time_limit_seconds = cpu_time_limit_seconds
        self._max_request_bytes = max_request_bytes
        self._max_response_bytes = max_response_bytes

    @staticmethod
    def _kill_process_tree(process: subprocess.Popen[bytes]) -> None:
        # Bubblewrap's --die-with-parent handles namespace descendants after
        # the launcher exits. Only signal the host process group while its
        # leader is still alive, avoiding PID/PGID reuse after reaping.
        if process.poll() is not None:
            return
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except OSError:
            try:
                process.kill()
            except OSError:
                pass
        try:
            process.wait(timeout=3.0)
        except subprocess.TimeoutExpired:
            try:
                process.kill()
            except OSError:
                pass
            try:
                process.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                raise LinuxSandboxLaunchError("sandbox_cleanup_timeout") from None

    def read(
        self,
        capability: str,
        request: Mapping[str, object],
        *,
        timeout_seconds: float,
    ) -> Mapping[str, object]:
        if not sys.platform.startswith("linux"):
            raise LinuxSandboxLaunchError("linux_sandbox_platform_required")
        if capability != "public_market_data.read":
            raise LinuxSandboxLaunchError("capability_not_read_only")
        if not isinstance(request, Mapping):
            raise LinuxSandboxLaunchError("invalid_request")
        if isinstance(timeout_seconds, bool):
            raise LinuxSandboxLaunchError("invalid_timeout")
        try:
            timeout = float(timeout_seconds)
        except (TypeError, ValueError, OverflowError):
            raise LinuxSandboxLaunchError("invalid_timeout") from None
        if not 0.1 <= timeout <= 60:
            raise LinuxSandboxLaunchError("invalid_timeout")

        payload = {
            "capability": capability,
            "request": request,
            "timeout_seconds": timeout,
            "memory_limit_mb": self._memory_limit_mb,
            "cpu_time_limit_seconds": self._cpu_time_limit_seconds,
        }
        try:
            encoded = json.dumps(
                payload, ensure_ascii=False, allow_nan=False, separators=(",", ":")
            ).encode("utf-8")
        except (TypeError, ValueError, RecursionError, OverflowError):
            raise LinuxSandboxLaunchError("invalid_request") from None
        if len(encoded) > self._max_request_bytes:
            raise LinuxSandboxLaunchError("request_too_large")

        # -S disables site initialization. The application path is explicitly
        # inserted from the package; no host PYTHONPATH or site-packages is used.
        bootstrap = (
            "import os,sys; "
            "sys.path.insert(0, os.path.join(os.environ['PYTHONHOME'], 'app')); "
            "from PC_ENGINE.core.connector_worker_bootstrap import main; "
            "raise SystemExit(main())"
        )
        command = [
            str(self._runtime_manifest.executable),
            "-S",
            "-c",
            bootstrap,
            self._factory_reference,
        ]
        try:
            argv = build_linux_bwrap_command(
                command,
                runtime_manifest=self._runtime_manifest,
                python_home=self._python_home,
                runtime_library_path=self._runtime_library_path,
                bwrap_path=self._bwrap_path,
            )
        except (SandboxUnavailable, ValueError, OSError):
            raise LinuxSandboxLaunchError("sandbox_configuration_denied") from None

        process: subprocess.Popen[bytes] | None = None
        selector: selectors.BaseSelector | None = None
        input_selector: selectors.BaseSelector | None = None
        deadline = time.monotonic() + timeout + 2.0
        try:
            process = subprocess.Popen(
                argv,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                cwd="/",
                env={"PATH": os.defpath, "LANG": "C"},
                close_fds=True,
                start_new_session=True,
                bufsize=0,
            )
            assert process.stdin is not None and process.stdout is not None
            try:
                input_fd = process.stdin.fileno()
                os.set_blocking(input_fd, False)
                input_selector = selectors.DefaultSelector()
                input_selector.register(process.stdin, selectors.EVENT_WRITE)
                remaining_input = memoryview(encoded)
                while remaining_input:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise LinuxSandboxLaunchError("sandbox_worker_timeout")
                    if not input_selector.select(remaining):
                        raise LinuxSandboxLaunchError("sandbox_worker_timeout")
                    try:
                        written = os.write(input_fd, remaining_input)
                    except BlockingIOError:
                        continue
                    if written <= 0:
                        raise LinuxSandboxLaunchError("sandbox_worker_input_failed")
                    remaining_input = remaining_input[written:]
                process.stdin.close()
            except (BrokenPipeError, OSError):
                raise LinuxSandboxLaunchError("sandbox_worker_input_failed") from None
            finally:
                if input_selector is not None:
                    input_selector.close()
                    input_selector = None

            selector = selectors.DefaultSelector()
            selector.register(process.stdout, selectors.EVENT_READ)
            output = bytearray()
            eof = False
            while not eof or process.poll() is None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise LinuxSandboxLaunchError("sandbox_worker_timeout")
                events = selector.select(min(remaining, 0.2))
                for key, _ in events:
                    chunk = os.read(key.fd, min(65_536, self._max_response_bytes + 129 - len(output)))
                    if not chunk:
                        eof = True
                        selector.unregister(key.fileobj)
                        break
                    output.extend(chunk)
                    if len(output) > self._max_response_bytes + 128:
                        raise LinuxSandboxLaunchError("response_too_large")
                if eof and process.poll() is None:
                    try:
                        process.wait(timeout=min(remaining, 0.2))
                    except subprocess.TimeoutExpired:
                        pass

            try:
                process.wait(timeout=max(0.1, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                raise LinuxSandboxLaunchError("sandbox_worker_timeout") from None
            if not output:
                raise LinuxSandboxLaunchError("sandbox_worker_failed")
            try:
                envelope: Any = json.loads(output.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                raise LinuxSandboxLaunchError("invalid_worker_response") from None
            if not isinstance(envelope, dict) or envelope.get("ok") is not True:
                error = envelope.get("error") if isinstance(envelope, dict) else None
                if error in {
                    "response_too_large",
                    "request_too_large",
                    "worker_resource_limits_unavailable",
                    "connector_startup_failed",
                    "connector_execution_failed",
                }:
                    reason = envelope.get("reason") if isinstance(envelope, dict) else None
                    if isinstance(reason, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,63}", reason):
                        raise LinuxSandboxLaunchError(f"{error}:{reason}")
                    raise LinuxSandboxLaunchError(error)
                raise LinuxSandboxLaunchError("connector_execution_failed")
            if process.returncode != 0:
                raise LinuxSandboxLaunchError("connector_execution_failed")
            data = envelope.get("data")
            if not isinstance(data, dict):
                raise LinuxSandboxLaunchError("invalid_worker_response")
            return data
        except LinuxSandboxLaunchError:
            raise
        except (OSError, ValueError, subprocess.SubprocessError):
            raise LinuxSandboxLaunchError("sandbox_launch_failed") from None
        finally:
            if input_selector is not None:
                input_selector.close()
            if selector is not None:
                selector.close()
            if process is not None:
                self._kill_process_tree(process)
                if process.stdin is not None:
                    process.stdin.close()
                if process.stdout is not None:
                    process.stdout.close()
