from __future__ import annotations

from threading import Lock
from types import SimpleNamespace

from PC_ENGINE.core.platform_connectors import (
    AccessMethod,
    ConnectorCategory,
    ConnectorHealth,
    ConnectorManifest,
)
from PC_ENGINE.services import public_connector_registry as module


class FakeAdapter:
    def __init__(self, venue: str):
        self.venue = venue
        self.calls = []

    def read(self, capability, request, *, timeout_seconds):
        self.calls.append((capability, dict(request), timeout_seconds))
        return {"venue": self.venue, "symbol": request.get("symbol")}


def _factory(venue, *, timeout_ms, client=None, lock=None):
    manifest = ConnectorManifest(
        provider_id=f"ccxt.{venue}.spot",
        display_name=f"{venue.upper()} public market data",
        category=ConnectorCategory.MARKET_DATA,
        access_method=AccessMethod.OFFICIAL_API,
        capabilities=frozenset({"public_market_data.read"}),
        requests_per_minute=60,
        request_timeout_seconds=timeout_ms / 1000,
        health=ConnectorHealth.AVAILABLE,
        adapter_version="test",
    )
    return manifest, FakeAdapter(venue)


def test_registry_uses_only_configured_public_radar_clients(monkeypatch):
    clients = {"binance": object(), "okx": object()}
    locks = {"binance": Lock(), "okx": Lock()}
    radar = SimpleNamespace(clients=clients, client_locks=locks)
    captured = []

    def factory(venue, *, timeout_ms, client=None, lock=None):
        captured.append((venue, timeout_ms, client, lock))
        return _factory(venue, timeout_ms=timeout_ms, client=client, lock=lock)

    monkeypatch.setattr(module, "build_public_exchange_connector", factory)
    registry, status = module.build_public_connector_registry(
        {
            "radar": {
                "enabled": True,
                "observational_only": True,
                "request_timeout_ms": 12_000,
                "polling_exchanges": ["binance", "okx", "binance", "missing", "Bad Venue"],
            }
        },
        paper_mode=True,
        market_radar=radar,
    )

    assert status["state"] == "DEGRADED"
    assert status["paper_only"] is True
    assert status["execution_authority"] is False
    assert status["private_credentials_used"] is False
    assert status["registered_provider_ids"] == [
        "ccxt.binance.spot",
        "ccxt.okx.spot",
    ]
    assert {item["reason"] for item in status["unavailable_venues"]} == {
        "adapter_unavailable",
        "invalid_venue_id",
    }
    assert captured == [
        ("binance", 12_000, clients["binance"], locks["binance"]),
        ("okx", 12_000, clients["okx"], locks["okx"]),
    ]

    result = registry.execute_read(
        "ccxt.binance.spot",
        "public_market_data.read",
        {"operation": "ticker", "symbol": "BTC/USDT"},
    )
    assert result.ok
    assert result.data == {"venue": "binance", "symbol": "BTC/USDT"}


def test_registry_does_not_register_when_not_paper_or_observational(monkeypatch):
    calls = []
    monkeypatch.setattr(
        module,
        "build_public_exchange_connector",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )
    radar = SimpleNamespace(clients={"binance": object()}, client_locks={"binance": Lock()})
    config = {
        "radar": {
            "enabled": True,
            "observational_only": True,
            "polling_exchanges": ["binance"],
        }
    }

    registry, status = module.build_public_connector_registry(
        config, paper_mode=False, market_radar=radar
    )
    assert registry.list_connectors() == ()
    assert status["state"] == "DISABLED"

    registry, status = module.build_public_connector_registry(
        {"radar": {**config["radar"], "observational_only": False}},
        paper_mode=True,
        market_radar=radar,
    )
    assert registry.list_connectors() == ()
    assert status["state"] == "DISABLED"
    assert calls == []


def test_registry_clamps_invalid_timeout_and_handles_no_configured_venues(monkeypatch):
    calls = []
    monkeypatch.setattr(
        module,
        "build_public_exchange_connector",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )
    radar = SimpleNamespace(clients={}, client_locks={})
    registry, status = module.build_public_connector_registry(
        {
            "radar": {
                "enabled": True,
                "observational_only": True,
                "request_timeout_ms": "invalid",
                "polling_exchanges": [],
            }
        },
        paper_mode=True,
        market_radar=radar,
    )
    assert registry.list_connectors() == ()
    assert status["state"] == "EMPTY"
    assert status["request_timeout_ms"] == 8000
    assert status["unavailable_venues"] == []
    assert calls == []
