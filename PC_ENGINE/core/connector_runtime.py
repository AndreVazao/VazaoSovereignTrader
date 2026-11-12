from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Mapping, Protocol

from PC_ENGINE.core.platform_connectors import (
    ConnectorHealth,
    ConnectorManifest,
    READ_ONLY_CAPABILITIES,
    authorize_capability,
)


class ConnectorAdapter(Protocol):
    """Provider adapter contract. Implementations must use official, permitted interfaces."""

    def read(self, capability: str, request: Mapping[str, object]) -> Mapping[str, object]:
        """Return a bounded, JSON-compatible read-only snapshot."""


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


class ConnectorRegistry:
    """In-process registry with fail-closed authorization and bounded responses.

    This registry performs no discovery, network calls, credential loading, or
    cloud provisioning. Those responsibilities belong to separately reviewed
    provider adapters and deployment services.
    """

    def __init__(self, *, max_request_bytes: int = 32_768,
                 max_response_bytes: int = 262_144) -> None:
        if not 1 <= max_request_bytes <= 1_048_576:
            raise ValueError("invalid_request_limit")
        if not 1 <= max_response_bytes <= 4_194_304:
            raise ValueError("invalid_response_limit")
        self._entries: dict[str, _Registration] = {}
        self._max_request_bytes = max_request_bytes
        self._max_response_bytes = max_response_bytes

    def register(self, manifest: ConnectorManifest, adapter: ConnectorAdapter, *,
                 owner_grants: frozenset[str] = frozenset(),
                 provider_verified: frozenset[str] = frozenset()) -> None:
        if manifest.provider_id in self._entries:
            raise ValueError("connector_already_registered")
        if not callable(getattr(adapter, "read", None)):
            raise ValueError("connector_read_method_required")
        self._entries[manifest.provider_id] = _Registration(
            manifest=manifest,
            adapter=adapter,
            owner_grants=frozenset(owner_grants),
            provider_verified=frozenset(provider_verified),
        )

    def unregister(self, provider_id: str) -> bool:
        return self._entries.pop(provider_id, None) is not None

    def list_connectors(self) -> tuple[dict[str, object], ...]:
        """Expose safe metadata only; never expose grants, adapter objects or secrets."""
        return tuple({
            "provider_id": item.manifest.provider_id,
            "display_name": item.manifest.display_name,
            "category": item.manifest.category.value,
            "access_method": item.manifest.access_method.value,
            "health": item.manifest.health.value,
            "capabilities": sorted(item.manifest.capabilities),
            "adapter_version": item.manifest.adapter_version,
        } for item in sorted(self._entries.values(),
                             key=lambda value: value.manifest.provider_id))

    def execute_read(self, provider_id: str, capability: str,
                     request: Mapping[str, object] | None = None) -> ConnectorExecution:
        entry = self._entries.get(provider_id)
        if entry is None:
            return ConnectorExecution(False, provider_id, capability,
                                      error="connector_not_found")
        if not isinstance(capability, str) or capability not in READ_ONLY_CAPABILITIES:
            return ConnectorExecution(False, provider_id, capability,
                                      error="capability_not_read_only")
        if not authorize_capability(
            entry.manifest, capability,
            owner_granted=entry.owner_grants,
            provider_verified=entry.provider_verified,
        ):
            return ConnectorExecution(False, provider_id, capability,
                                      error="capability_not_authorized")

        payload = request if request is not None else {}
        if not isinstance(payload, Mapping):
            return ConnectorExecution(False, provider_id, capability,
                                      error="invalid_request")
        try:
            encoded_request = json.dumps(payload, ensure_ascii=False,
                                         allow_nan=False, separators=(",", ":")).encode("utf-8")
        except (TypeError, ValueError):
            return ConnectorExecution(False, provider_id, capability,
                                      error="request_not_json_serializable")
        if len(encoded_request) > self._max_request_bytes:
            return ConnectorExecution(False, provider_id, capability,
                                      error="request_too_large")

        try:
            result = entry.adapter.read(capability, dict(payload))
            if not isinstance(result, Mapping):
                raise ValueError("invalid_adapter_result")
            encoded_result = json.dumps(result, ensure_ascii=False, allow_nan=False,
                                        separators=(",", ":")).encode("utf-8")
            if len(encoded_result) > self._max_response_bytes:
                return ConnectorExecution(False, provider_id, capability,
                                          error="response_too_large")
            # Detach caller-owned mutable mappings from adapter state.
            safe_result = json.loads(encoded_result.decode("utf-8"))
            return ConnectorExecution(True, provider_id, capability, data=safe_result)
        except Exception:
            # Do not leak provider exception text, headers, URLs or credential material.
            return ConnectorExecution(False, provider_id, capability,
                                      error="connector_execution_failed")
