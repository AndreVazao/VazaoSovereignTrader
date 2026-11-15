from __future__ import annotations

import json
import multiprocessing
import os
from collections.abc import Mapping
from typing import Any, Callable

from PC_ENGINE.core.connector_worker_limits import (
    apply_child_resource_limits,
    assign_windows_job_limits,
    close_windows_job,
    validate_worker_limits,
)


class IsolatedConnectorError(RuntimeError):
    """Sanitized failure raised by the one-shot connector worker."""


_SECRET_ENV_MARKERS = (
    "TOKEN",
    "SECRET",
    "PASSWORD",
    "CREDENTIAL",
    "API_KEY",
    "APIKEY",
    "PRIVATE_KEY",
    "AUTHORIZATION",
    "COOKIE",
)


def _sanitize_worker_environment() -> None:
    """Remove inherited credential-shaped environment variables before adapter code."""
    for name in tuple(os.environ):
        normalized = name.upper()
        if any(marker in normalized for marker in _SECRET_ENV_MARKERS):
            os.environ.pop(name, None)


def _send_error(send_connection: Any, code: str) -> None:
    try:
        send_connection.send_bytes(
            json.dumps({"ok": False, "error": code}).encode("ascii")
        )
    except (BrokenPipeError, EOFError, OSError):
        pass


def _worker_entry(
    send_connection: Any,
    control_connection: Any,
    adapter_factory: Callable[[], Any],
    capability: str,
    request_bytes: bytes,
    timeout_seconds: float,
    max_response_bytes: int,
    memory_limit_mb: int,
    cpu_time_limit_seconds: int,
    startup_grace_seconds: float,
) -> None:
    """Spawn target. Parent must apply Windows Job Object before releasing it."""
    try:
        send_connection.send_bytes(b'{"ready":"bootstrap"}')
        if not control_connection.poll(startup_grace_seconds):
            return
        if control_connection.recv_bytes(128) != b"start":
            return
        apply_child_resource_limits(memory_limit_mb, cpu_time_limit_seconds)
    except BaseException:
        _send_error(send_connection, "worker_resource_limits_unavailable")
        try:
            send_connection.close()
            control_connection.close()
        finally:
            return

    _sanitize_worker_environment()
    try:
        request = json.loads(request_bytes.decode("utf-8"))
        adapter = adapter_factory()
    except BaseException:
        _send_error(send_connection, "connector_startup_failed")
        try:
            send_connection.close()
            control_connection.close()
        finally:
            return

    try:
        send_connection.send_bytes(b'{"ready":true,"limits":true}')
        result = adapter.read(
            capability,
            request,
            timeout_seconds=timeout_seconds,
        )
        if not isinstance(result, Mapping):
            raise TypeError("invalid_adapter_result")
        response = json.dumps(
            result,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")
        if len(response) > max_response_bytes:
            _send_error(send_connection, "response_too_large")
        else:
            send_connection.send_bytes(b'{"ok":true,"data":' + response + b"}")
    except BaseException:
        # Never serialize exception text, traceback, URLs, headers or secrets.
        _send_error(send_connection, "connector_execution_failed")
    finally:
        send_connection.close()
        control_connection.close()


class IsolatedConnectorAdapter:
    """One-shot worker with OS-enforced CPU and memory limits.

    POSIX workers receive RLIMIT_AS and RLIMIT_CPU before adapter code runs.
    Windows workers are assigned to a kill-on-close Job Object before release.
    This is still not a complete security sandbox: filesystem isolation and
    network egress allowlists are not implemented. Do not load untrusted
    third-party adapters until those controls and provider policy are added.
    """

    def __init__(
        self,
        adapter_factory: Callable[[], Any],
        *,
        max_request_bytes: int = 32_768,
        max_response_bytes: int = 262_144,
        startup_grace_seconds: float = 5.0,
        memory_limit_mb: int = 384,
        cpu_time_limit_seconds: int = 30,
    ) -> None:
        if not callable(adapter_factory):
            raise ValueError("adapter_factory_required")
        if not 1 <= max_request_bytes <= 1_048_576:
            raise ValueError("invalid_request_limit")
        if not 1 <= max_response_bytes <= 4_194_304:
            raise ValueError("invalid_response_limit")
        if not 0.1 <= float(startup_grace_seconds) <= 30:
            raise ValueError("invalid_startup_grace")
        try:
            validate_worker_limits(memory_limit_mb, cpu_time_limit_seconds)
        except ValueError as exc:
            raise ValueError(str(exc)) from None
        self._factory = adapter_factory
        self._max_request_bytes = max_request_bytes
        self._max_response_bytes = max_response_bytes
        self._startup_grace_seconds = float(startup_grace_seconds)
        self._memory_limit_mb = memory_limit_mb
        self._cpu_time_limit_seconds = cpu_time_limit_seconds

    def read(
        self,
        capability: str,
        request: Mapping[str, object],
        *,
        timeout_seconds: float,
    ) -> Mapping[str, object]:
        if not isinstance(capability, str) or not capability:
            raise IsolatedConnectorError("invalid_capability")
        try:
            timeout = float(timeout_seconds)
        except (TypeError, ValueError, OverflowError):
            raise IsolatedConnectorError("invalid_timeout") from None
        if not 0.1 <= timeout <= 60:
            raise IsolatedConnectorError("invalid_timeout")
        if not isinstance(request, Mapping):
            raise IsolatedConnectorError("invalid_request")
        try:
            request_bytes = json.dumps(
                request,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            ).encode("utf-8")
        except (TypeError, ValueError):
            raise IsolatedConnectorError("invalid_request") from None
        if len(request_bytes) > self._max_request_bytes:
            raise IsolatedConnectorError("request_too_large")

        context = multiprocessing.get_context("spawn")
        receive_connection, send_connection = context.Pipe(duplex=False)
        control_connection = context.Pipe(duplex=True)[0]
        parent_control = context.Pipe(duplex=True)[1]
        process = context.Process(
            target=_worker_entry,
            args=(
                send_connection,
                control_connection,
                self._factory,
                capability,
                request_bytes,
                timeout,
                self._max_response_bytes,
                self._memory_limit_mb,
                self._cpu_time_limit_seconds,
                self._startup_grace_seconds,
            ),
            daemon=True,
        )
        windows_job = None
        try:
            process.start()
            send_connection.close()
            if not receive_connection.poll(self._startup_grace_seconds):
                raise IsolatedConnectorError("connector_startup_timeout")
            try:
                bootstrap = json.loads(
                    receive_connection.recv_bytes(128).decode("utf-8")
                )
            except (EOFError, OSError, UnicodeDecodeError, json.JSONDecodeError):
                raise IsolatedConnectorError("connector_startup_failed") from None
            if not isinstance(bootstrap, dict) or bootstrap.get("ready") != "bootstrap":
                raise IsolatedConnectorError("connector_startup_failed")

            if os.name == "nt":
                try:
                    windows_job = assign_windows_job_limits(
                        process,
                        self._memory_limit_mb,
                        self._cpu_time_limit_seconds,
                    )
                except BaseException:
                    raise IsolatedConnectorError(
                        "worker_resource_limits_unavailable"
                    ) from None

            parent_control.send_bytes(b"start")
            if not receive_connection.poll(self._startup_grace_seconds):
                raise IsolatedConnectorError("connector_startup_timeout")
            try:
                startup = json.loads(
                    receive_connection.recv_bytes(256).decode("utf-8")
                )
            except (EOFError, OSError, UnicodeDecodeError, json.JSONDecodeError):
                raise IsolatedConnectorError("connector_startup_failed") from None
            if not isinstance(startup, dict) or startup.get("ready") is not True:
                error = startup.get("error") if isinstance(startup, dict) else None
                if error == "worker_resource_limits_unavailable":
                    raise IsolatedConnectorError(error)
                raise IsolatedConnectorError("connector_startup_failed")
            if startup.get("limits") is not True:
                raise IsolatedConnectorError("worker_resource_limits_unavailable")

            if not receive_connection.poll(timeout):
                raise IsolatedConnectorError("connector_timeout")
            try:
                raw = receive_connection.recv_bytes(self._max_response_bytes + 128)
            except (EOFError, OSError):
                raise IsolatedConnectorError("connector_worker_failed") from None
            try:
                envelope = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                raise IsolatedConnectorError("invalid_worker_response") from None
            if not isinstance(envelope, dict) or envelope.get("ok") is not True:
                error = envelope.get("error") if isinstance(envelope, dict) else None
                if error == "response_too_large":
                    raise IsolatedConnectorError("response_too_large")
                raise IsolatedConnectorError("connector_execution_failed")
            data = envelope.get("data")
            if not isinstance(data, dict):
                raise IsolatedConnectorError("invalid_worker_response")
            return data
        finally:
            receive_connection.close()
            try:
                parent_control.close()
            except OSError:
                pass
            if process.pid is not None:
                if process.is_alive():
                    process.terminate()
                process.join(timeout=2.0)
                if process.is_alive() and hasattr(process, "kill"):
                    process.kill()
                    process.join(timeout=2.0)
            try:
                control_connection.close()
            except OSError:
                pass
            try:
                send_connection.close()
            except OSError:
                pass
            close_windows_job(windows_job)
