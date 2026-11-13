from __future__ import annotations

from types import SimpleNamespace

from flask import Flask, jsonify

from PC_ENGINE.api.public_connectors import register_public_connector_routes
from PC_ENGINE.core.connector_runtime import ConnectorRegistry
from PC_ENGINE.core.platform_connectors import (
    AccessMethod,
    ConnectorCategory,
    ConnectorHealth,
    ConnectorManifest,
)


class FakeAdapter:
    def __init__(self):
        self.calls = []

    def read(self, capability, request, *, timeout_seconds):
        self.calls.append((capability, dict(request), timeout_seconds))
        return {"venue": "binance", "symbol": request.get("symbol")}


def _client(*, status="RUNNING", requests_per_minute=60):
    app = Flask(__name__)
    adapter = FakeAdapter()
    registry = ConnectorRegistry()
    capability = "public_market_data.read"
    grants = frozenset({capability})
    registry.register(
        ConnectorManifest(
            provider_id="ccxt.binance.spot",
            display_name="BINANCE public market data",
            category=ConnectorCategory.MARKET_DATA,
            access_method=AccessMethod.OFFICIAL_API,
            capabilities=grants,
            requests_per_minute=requests_per_minute,
            request_timeout_seconds=3.0,
            health=ConnectorHealth.AVAILABLE,
        ),
        adapter,
        owner_grants=grants,
        provider_verified=grants,
    )
    engine = SimpleNamespace(
        paper=True,
        state=SimpleNamespace(status=status),
        connector_registry=registry,
        connector_registry_status={
            "state": "READY",
            "private_credentials_used": False,
            "execution_authority": False,
        },
    )
    authorized = {"value": False}

    def require_scope(scope):
        assert scope == "read_private_state"
        if not authorized["value"]:
            raise PermissionError("scope_required")

    app.register_error_handler(
        PermissionError,
        lambda _: (jsonify({"ok": False, "error": "unauthorized"}), 401),
    )
    register_public_connector_routes(app, engine, require_scope=require_scope)
    return app.test_client(), authorized, adapter, engine


def test_connector_list_requires_owner_authentication_and_exposes_safe_metadata():
    client, authorized, _, _ = _client()
    assert client.get("/connectors").status_code == 401

    authorized["value"] = True
    response = client.get("/connectors")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["connectors"][0]["provider_id"] == "ccxt.binance.spot"
    assert payload["paper_only"] is True
    assert payload["execution_authority"] is False
    assert "owner_grants" not in str(payload)
    assert "provider_verified" not in str(payload)
    assert response.headers["Cache-Control"] == "no-store"


def test_connector_read_is_authenticated_bounded_and_read_only():
    client, authorized, adapter, _ = _client()
    body = {
        "capability": "public_market_data.read",
        "request": {"operation": "ticker", "symbol": "BTC/USDT"},
    }
    assert client.post("/connectors/ccxt.binance.spot/read", json=body).status_code == 401

    authorized["value"] = True
    response = client.post("/connectors/ccxt.binance.spot/read", json=body)
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["data"] == {"venue": "binance", "symbol": "BTC/USDT"}
    assert payload["paper_only"] is True
    assert payload["execution_authority"] is False
    assert len(adapter.calls) == 1


def test_connector_api_rejects_mutation_capabilities_and_credentials():
    client, authorized, adapter, _ = _client()
    authorized["value"] = True

    mutation = client.post(
        "/connectors/ccxt.binance.spot/read",
        json={"capability": "orders.create", "request": {"symbol": "BTC/USDT"}},
    )
    assert mutation.status_code == 403
    assert mutation.get_json()["error"] == "capability_not_read_only"

    credential = client.post(
        "/connectors/ccxt.binance.spot/read",
        json={
            "capability": "public_market_data.read",
            "request": {"operation": "ticker", "symbol": "BTC/USDT", "api_key": "must-not-be-accepted"},
        },
    )
    assert credential.status_code == 400
    assert credential.get_json()["error"] == "credential_fields_not_accepted"
    assert adapter.calls == []


def test_connector_api_rejects_unexpected_top_level_fields_and_non_json():
    client, authorized, adapter, _ = _client()
    authorized["value"] = True

    extra = client.post(
        "/connectors/ccxt.binance.spot/read",
        json={
            "capability": "public_market_data.read",
            "request": {"operation": "ticker", "symbol": "BTC/USDT"},
            "token": "not-accepted",
        },
    )
    assert extra.status_code == 400

    non_json = client.post(
        "/connectors/ccxt.binance.spot/read",
        data="capability=public_market_data.read",
        content_type="application/x-www-form-urlencoded",
    )
    assert non_json.status_code == 415
    assert adapter.calls == []


def test_connector_api_blocks_reads_when_engine_is_not_running():
    client, authorized, _, engine = _client(status="OFF")
    authorized["value"] = True
    response = client.post(
        "/connectors/ccxt.binance.spot/read",
        json={
            "capability": "public_market_data.read",
            "request": {"operation": "ticker", "symbol": "BTC/USDT"},
        },
    )
    assert response.status_code == 503
    assert response.get_json()["error"] == "engine_not_running"


def test_connector_api_maps_registry_rate_limit_to_http_429():
    client, authorized, adapter, _ = _client(requests_per_minute=1)
    authorized["value"] = True
    body = {
        "capability": "public_market_data.read",
        "request": {"operation": "ticker", "symbol": "BTC/USDT"},
    }
    first = client.post("/connectors/ccxt.binance.spot/read", json=body)
    second = client.post("/connectors/ccxt.binance.spot/read", json=body)
    assert first.status_code == 200
    assert second.status_code == 429
    assert len(adapter.calls) == 1
