from __future__ import annotations

"""Minimal one-shot entry point for a worker already launched by a trusted sandbox parent.

The factory reference is supplied as a process argument by the trusted parent,
never by the worker's untrusted JSON request. This module does not create a
sandbox, launch processes, or load credentials.
"""

import contextlib
import importlib
import json
import math
import os
import re
import sys
from collections.abc import Mapping
from typing import Any

from PC_ENGINE.core.connector_worker_limits import apply_child_resource_limits

MAX_REQUEST_BYTES = 32_768
MAX_RESPONSE_BYTES = 262_144
_SECRET_ENV_MARKERS = (
    "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL", "API_KEY", "APIKEY",
    "ACCESS_KEY", "PRIVATE", "SIGNING_KEY", "BEARER", "CLIENT_SECRET",
    "AUTHORIZATION", "COOKIE",
)
_FACTORY_PATH = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*:"
    r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$"
)


def _sanitize_environment() -> None:
    for name in tuple(os.environ):
        if any(marker in name.upper() for marker in _SECRET_ENV_MARKERS):
            os.environ.pop(name, None)
    for name in ("PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP", "PYTHONINSPECT"):
        os.environ.pop(name, None)


def _resolve_factory(path: str) -> Any:
    if not isinstance(path, str) or not _FACTORY_PATH.fullmatch(path):
        raise ValueError("invalid_factory_reference")
    module_name, qualified_name = path.split(":", 1)
    value: Any = importlib.import_module(module_name)
    for component in qualified_name.split("."):
        value = getattr(value, component)
    if not callable(value):
        raise ValueError("factory_not_callable")
    return value


def execute_request(
    payload: Mapping[str, Any],
    *,
    factory_reference: str,
    factory_resolver: Any = _resolve_factory,
) -> dict[str, Any]:
    if not isinstance(payload, Mapping) or set(payload) != {
        "capability", "request", "timeout_seconds",
        "memory_limit_mb", "cpu_time_limit_seconds",
    }:
        raise ValueError("invalid_worker_request")
    capability = payload["capability"]
    request = payload["request"]
    timeout = payload["timeout_seconds"]
    memory_limit = payload["memory_limit_mb"]
    cpu_limit = payload["cpu_time_limit_seconds"]
    if not isinstance(capability, str) or not capability or len(capability) > 128:
        raise ValueError("invalid_capability")
    if not isinstance(request, Mapping):
        raise ValueError("invalid_request")
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
        raise ValueError("invalid_timeout")
    if not math.isfinite(float(timeout)) or not 0.1 <= float(timeout) <= 60:
        raise ValueError("invalid_timeout")
    if isinstance(memory_limit, bool) or not isinstance(memory_limit, int):
        raise ValueError("invalid_memory_limit")
    if isinstance(cpu_limit, bool) or not isinstance(cpu_limit, int):
        raise ValueError("invalid_cpu_limit")

    # Resource boundaries are established before importing adapter modules.
    apply_child_resource_limits(memory_limit, cpu_limit)
    factory = factory_resolver(factory_reference)
    adapter = factory()
    with contextlib.redirect_stdout(sys.stderr):
        result = adapter.read(
            capability,
            request,
            timeout_seconds=float(timeout),
        )
    if not isinstance(result, Mapping):
        raise ValueError("invalid_adapter_result")
    encoded = json.dumps(
        result, ensure_ascii=False, allow_nan=False, separators=(",", ":")
    ).encode("utf-8")
    if len(encoded) > MAX_RESPONSE_BYTES:
        raise ValueError("response_too_large")
    return {"ok": True, "data": json.loads(encoded.decode("utf-8"))}


def main() -> int:
    _sanitize_environment()
    try:
        if len(sys.argv) != 2:
            raise ValueError("trusted_factory_argument_required")
        raw = sys.stdin.buffer.read(MAX_REQUEST_BYTES + 1)
        if len(raw) > MAX_REQUEST_BYTES:
            envelope = {"ok": False, "error": "request_too_large"}
        else:
            payload = json.loads(raw.decode("utf-8"))
            envelope = execute_request(
                payload,
                factory_reference=sys.argv[1],
            )
    except BaseException:
        # Do not expose exception messages, tracebacks, provider URLs or secrets.
        envelope = {"ok": False, "error": "connector_execution_failed"}
    try:
        encoded = json.dumps(
            envelope, ensure_ascii=True, allow_nan=False, separators=(",", ":")
        ).encode("ascii")
        if len(encoded) > MAX_RESPONSE_BYTES + 128:
            encoded = b'{"ok":false,"error":"response_too_large"}'
        sys.stdout.buffer.write(encoded + b"\n")
        sys.stdout.buffer.flush()
        return 0 if envelope.get("ok") is True else 1
    except BaseException:
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
