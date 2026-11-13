from __future__ import annotations

import json
import multiprocessing
from collections.abc import Mapping
from typing import Any, Callable


class IsolatedConnectorError(RuntimeError):
    """Sanitized failure raised by the one-shot connector worker."""


def _worker_entry(
    send_connection: Any,
    adapter_factory: Callable[[], Any],
    capability: str,
    request_bytes: bytes,
    timeout_seconds: float,
    max_response_bytes: int,
) -> None:
    """Spawn target. Only strict JSON crosses the process boundary."""
    try:
        request = json.loads(request_bytes.decode("utf-8"))
        adapter = adapter_factory()
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
            send_connection.send_bytes(b'{"ok":false,"error":"response_too_large"}')
        else:
            send_connection.send_bytes(b'{"ok":true,"data":' + response + b"}")
    except BaseException:
        # Never serialize exception text, traceback, URLs, headers or secrets.
        try:
            send_connection.send_bytes(b'{"ok":false,"error":"connector_execution_failed"}')
        except (BrokenPipeError, EOFError, OSError):
            pass
    finally:
        send_connection.close()


class IsolatedConnectorAdapter:
    """One-shot spawned-process wrapper for explicitly trusted adapter factories.

    This provides process termination on timeout and strict JSON IPC. It is not
    an OS security sandbox: the child retains the host user's permissions and
    must not be used for untrusted third-party code until OS-level restrictions,
    resource quotas and provider-specific policy are added.
    """

    def __init__(
        self,
        adapter_factory: Callable[[], Any],
        *,
        max_request_bytes: int = 32_768,
        max_response_bytes: int = 262_144,
        startup_grace_seconds: float = 5.0,
    ) -> None:
        if not callable(adapter_factory):
            raise ValueError("adapter_factory_required")
        if not 1 <= max_request_bytes <= 1_048_576:
            raise ValueError("invalid_request_limit")
        if not 1 <= max_response_bytes <= 4_194_304:
            raise ValueError("invalid_response_limit")
        if not 0.1 <= float(startup_grace_seconds) <= 30:
            raise ValueError("invalid_startup_grace")
        self._factory = adapter_factory
        self._max_request_bytes = max_request_bytes
        self._max_response_bytes = max_response_bytes
        self._startup_grace_seconds = float(startup_grace_seconds)

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
        process = context.Process(
            target=_worker_entry,
            args=(
                send_connection,
                self._factory,
                capability,
                request_bytes,
                timeout,
                self._max_response_bytes,
            ),
            daemon=True,
        )
        try:
            process.start()
            send_connection.close()
            wait_seconds = min(60.0, timeout + self._startup_grace_seconds)
            if not receive_connection.poll(wait_seconds):
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
            if process.pid is not None:
                if process.is_alive():
                    process.terminate()
                process.join(timeout=2.0)
                if process.is_alive() and hasattr(process, "kill"):
                    process.kill()
                    process.join(timeout=2.0)
            try:
                send_connection.close()
            except OSError:
                pass
