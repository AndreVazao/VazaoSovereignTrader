from __future__ import annotations

import re
from collections.abc import Mapping
from threading import Lock
from typing import Any

from PC_ENGINE.core.connector_runtime import ConnectorRegistry
from PC_ENGINE.exchanges.public_market_data import build_public_exchange_connector


_PUBLIC_MARKET_DATA = frozenset({"public_market_data.read"})
_VENUE_ID = re.compile(r"^[a-z0-9_]{2,32}$")


def build_public_connector_registry(
    config: Mapping[str, Any],
    *,
    paper_mode: bool,
    market_radar: Any,
) -> tuple[ConnectorRegistry, dict[str, Any]]:
    """Register configured first-party public CCXT adapters without extra clients.

    The configured radar venue list is the owner's allowlist for public market
    data. Adapters reuse the collector's unauthenticated CCXT clients and their
    locks, so enabling this API does not create duplicate exchange sessions.
    No private credentials or account methods are used.
    """
    registry = ConnectorRegistry()
    radar_cfg = config.get("radar", {})
    if not isinstance(radar_cfg, Mapping):
        radar_cfg = {}

    if (
        not paper_mode
        or not bool(radar_cfg.get("enabled", True))
        or not bool(radar_cfg.get("observational_only", True))
        or market_radar is None
    ):
        return registry, {
            "state": "DISABLED",
            "reason": "paper_observational_runtime_required",
            "paper_only": bool(paper_mode),
            "execution_authority": False,
            "private_credentials_used": False,
            "registered_provider_ids": [],
            "unavailable_venues": [],
        }

    configured = radar_cfg.get("polling_exchanges", [])
    if not isinstance(configured, (list, tuple)):
        configured = []

    try:
        timeout_ms = int(radar_cfg.get("request_timeout_ms", 8000))
    except (TypeError, ValueError, OverflowError):
        timeout_ms = 8000
    timeout_ms = max(1000, min(60000, timeout_ms))

    clients = getattr(market_radar, "clients", {})
    client_locks = getattr(market_radar, "client_locks", {})
    if not isinstance(clients, Mapping):
        clients = {}
    if not isinstance(client_locks, Mapping):
        client_locks = {}

    seen: set[str] = set()
    registered: list[str] = []
    unavailable: list[dict[str, str]] = []

    for raw_venue in configured:
        if not isinstance(raw_venue, str):
            continue
        venue = raw_venue.strip().lower()
        if not venue or venue in seen:
            continue
        seen.add(venue)
        if not _VENUE_ID.fullmatch(venue):
            unavailable.append({"venue": venue[:32], "reason": "invalid_venue_id"})
            continue

        client = clients.get(venue)
        if client is None:
            unavailable.append({"venue": venue, "reason": "adapter_unavailable"})
            continue

        shared_lock = client_locks.get(venue)
        if shared_lock is None:
            # Test doubles and compatible custom MarketRadar instances may not
            # expose locks. Production MarketRadar always supplies a shared lock.
            shared_lock = Lock()

        try:
            manifest, adapter = build_public_exchange_connector(
                venue,
                timeout_ms=timeout_ms,
                client=client,
                lock=shared_lock,
            )
            registry.register(
                manifest,
                adapter,
                owner_grants=_PUBLIC_MARKET_DATA,
                provider_verified=_PUBLIC_MARKET_DATA,
            )
            registered.append(manifest.provider_id)
        except Exception as exc:
            # Keep provider URLs, request details and exception text out of diagnostics.
            unavailable.append({"venue": venue, "reason": type(exc).__name__})

    state = "READY" if registered and not unavailable else (
        "DEGRADED" if registered or unavailable else "EMPTY"
    )
    return registry, {
        "state": state,
        "source": "configured_radar_polling_exchanges",
        "health_semantics": "adapter_ready_not_remote_connectivity",
        "request_timeout_ms": timeout_ms,
        "configured_venues": sorted(seen),
        "registered_provider_ids": sorted(registered),
        "unavailable_venues": unavailable,
        "paper_only": True,
        "execution_authority": False,
        "private_credentials_used": False,
    }
