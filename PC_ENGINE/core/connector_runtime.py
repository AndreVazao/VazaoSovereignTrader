from __future__ import annotations

import json
import time
from collections import deque
from dataclasses import dataclass, field
from threading import Lock
from typing import Mapping, Protocol

from PC_ENGINE.core.platform_connectors import (
    ConnectorManifest,
    READ_ONLY_CAPABILITIES,
    authorize_capability,
)


class ConnectorAdapter(Protocol):
    """Provider adapter contract. Implementations must use official, permitted interfaces.

    Adapters receive the manifest timeout and MUST apply it to every blocking I/O
    operation they perform. The registry cannot forcibly interrupt arbitrary
    synchronous Python code running in-process; adapters that are not trusted
    first-party code require process isolation before they can be enabled.
    """

    def read(
        self,
        capability: str,
        request: Mapping[str, object],
        *,
        timeout_seconds: float,
    ) -> Mapping[str, object]:
        """Return a bounded, JSON-compatible read-only snapshot within the timeout."""


@dataclass(frozen=True)
class ConnectorExecution:
    ok: bool
    provider_id: str
    capability: str
    data: Mapping[str, object] | None = None
    error: str | None = None


@dataclass(frozen=True)
class _Registration:
    manifest: ConnectorManifest
    adapter: ConnectorAdapter
    owner_grants: frozenset[str]
    provider_verified: frozenset[str]
    request_times: deque[float] = field(default_factory=deque, repr=False)
    rate_lock: object = field(default_factory=Lock, repr=False)


class ConnectorRegistry:
    """In-process registry with fail-closed authorization and bounded execution.

    The registry enforces per-provider rolling request rates and JSON payload
    sizes. It forwards the manifest timeout to the adapter, but cannot preempt
    a non-cooperative in-process adapter. No discovery, network calls,
    credential loading, or cloud provisioning happen here.
    """

    def __init__(
        self,
        *,
        max_request_bytes: int = 32_768,
        max_response_bytes: int = 262_144,
    ) -> None:
        if not 1 <= max_request_bytes <= 1_048_576:
            raise ValueError("invalid_request_limit")
        if not 1 <= max_response_bytes <= 4_194_304:
            raise ValueError("invalid_response_limit")
        self._entries: dict[str, _Registration] = {}
        self._entries_lock = Lock()
        self._max_request_bytes = max_request_bytes
        self._max_response_bytes = max_response_bytes

    def register(
        self,
        manifest: ConnectorManifest,
        adapter: ConnectorAdapter,
        *,
        owner_grants: frozenset[str] = frozenset(),
        provider_verified: frozenset[str] = frozenset(),
    ) -> None:
        if not callable(getattr(adapter, "read", None)):
            raise ValueError("connector_read_method_required")
        registration = _Registration(
            manifest=manifest,
            adapter=adapter,
            owner_grants=frozenset(owner_grants),
            provider_verified=frozenset(provider_verified),
        )
        with self._entries_lock:
            if manifest.provider_id in self._entries:
                raise ValueError("connector_already_registered")
            self._entries[manifest.provider_id] = registration

    def unregister(self, provider_id: str) -> bool:
        with self._entries_lock:
            return self._entries.pop(provider_id, None) is not None

    def list_connectors(self) -> tuple[dict[str, object], ...]:
        """Expose safe metadata only; never expose grants, locks or adapter objects."""
        with self._entries_lock:
            entries = tuple(self._entries.values())
        return tuple(
            {
                "provider_id": item.manifest.provider_id,
                "display_name": item.manifest.display_name,
                "category": item.manifest.category.value,
                "access_method": item.manifest.access_method.value,
                "health": item.manifest.health.value,
                "capabilities": sorted(item.manifest.capabilities),
                "adapter_version": item.manifest.adapter_version,
            }
            for item in sorted(entries, key=lambda value: value.manifest.provider_id)
        )

    def execute_read(
        self,
        provider_id: str,
        capability: str,
        request: Mapping[str, object] | None = None,
    ) -> ConnectorExecution:
        with self._entries_lock:
            entry = self._entries.get(provider_id)
        if entry is None:
            return ConnectorExecution(
                False, provider_id, capability, error="connector_not_found"
            )
        if not isinstance(capability, str) or capability not in READ_ONLY_CAPABILITIES:
            return ConnectorExecution(
                False, provider_id, capability, error="capability_not_read_only"
            )
        if not authorize_capability(
            entry.manifest,
            capability,
            owner_granted=entry.owner_grants,
            provider_verified=entry.provider_verified,
        ):
            return ConnectorExecution(
                False, provider_id, capability, error="capability_not_authorized"
            )

        payload = request if request is not None else {}
        if not isinstance(payload, Mapping):
            return ConnectorExecution(False, provider_id, capability, error="invalid_request")
        try:
            encoded_request = json.dumps(
                payload,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            ).encode("utf-8")
        except (TypeError, ValueError):
            return ConnectorExecution(
                False,
                provider_id,
                capability,
                error="request_not_json_serializable",
            )
        if len(encoded_request) > self._max_request_bytes:
            return ConnectorExecution(
                False, provider_id, capability, error="request_too_large"
            )

        # Enforce a rolling 60-second budget per provider. Failed adapter calls
        # still consume a slot so failures cannot be used to bypass rate limits.
        now = time.monotonic()
        with entry.rate_lock:
            cutoff = now - 60.0
            while entry.request_times and entry.request_times[0] <= cutoff:
                entry.request_times.popleft()
            if len(entry.request_times) >= entry.manifest.requests_per_minute:
                return ConnectorExecution(
                    False, provider_id, capability, error="rate_limited"
                )
            entry.request_times.append(now)

        try:
            # Decode the already validated JSON to detach nested mutable values
            # and custom Mapping implementations from caller-owned state.
            safe_request = json.loads(encoded_request.decode("utf-8"))
            result = entry.adapter.read(
                capability,
                safe_request,
                timeout_seconds=entry.manifest.request_timeout_seconds,
            )
            if not isinstance(result, Mapping):
                raise ValueError("invalid_adapter_result")
            encoded_result = json.dumps(
                result,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            ).encode("utf-8")
            if len(encoded_result) > self._max_response_bytes:
                return ConnectorExecution(
                    False, provider_id, capability, error="response_too_large"
                )
            safe_result = json.loads(encoded_result.decode("utf-8"))
            return ConnectorExecution(
                True, provider_id, capability, data=safe_result
            )
        except Exception:
            # Never leak provider exception text, headers, URLs or credentials.
            return ConnectorExecution(
                False,
                provider_id,
                capability,
                error="connector_execution_failed",
            )
