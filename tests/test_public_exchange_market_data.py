from __future__ import annotations

import pytest

from PC_ENGINE.exchanges import public_market_data as module


class FakeExchange:
    def __init__(self, config):
        self.config = config
        self.timeout = config["timeout"]
        self.calls = []

    def fetch_ticker(self, symbol):
        self.calls.append(("ticker", symbol))
        return {
            "timestamp": 1000, "last": 10, "bid": 9.9, "ask": 10.1,
            "high": 12, "low": 8, "baseVolume": 20, "quoteVolume": 200,
        }

    def fetch_ohlcv(self, symbol, timeframe, limit):
        self.calls.append(("ohlcv", symbol, timeframe, limit))
        return [[1000, 1, 2, 0.5, 1.5, 10]] * limit

    def fetch_order_book(self, symbol, limit):
        self.calls.append(("order_book", symbol, limit))
        return {"timestamp": 1000, "bids": [[9.9, 2]], "asks": [[10.1, 3]]}


@pytest.fixture
def adapter(monkeypatch):
    monkeypatch.setattr(module.ccxt, "exchanges", ["binance", "okx", "coinbase"])
    monkeypatch.setattr(module.ccxt, "binance", FakeExchange, raising=False)
    monkeypatch.setattr(module.ccxt, "okx", FakeExchange, raising=False)
    monkeypatch.setattr(module.ccxt, "coinbase", FakeExchange, raising=False)
    return module.CcxtPublicMarketDataAdapter("binance")


def test_public_adapter_normalizes_ticker_without_credentials(adapter):
    result = adapter.read(
        "public_market_data.read", {"operation": "ticker", "symbol": "BTC/USDT"},
        timeout_seconds=3,
    )
    assert result["last"] == 10.0
    assert result["venue"] == "binance"
    assert adapter._client.config.keys() == {"enableRateLimit", "timeout", "options"}
    assert adapter._client.calls == [("ticker", "BTC/USDT")]
    assert adapter._client.timeout == 3000


def test_public_adapter_bounds_ohlcv_and_normalizes_rows(adapter):
    result = adapter.read(
        "public_market_data.read",
        {"operation": "ohlcv", "symbol": "ETH/USDT", "timeframe": "5m", "limit": 3},
        timeout_seconds=5,
    )
    assert len(result["candles"]) == 3
    assert result["candles"][0] == [1000.0, 1.0, 2.0, 0.5, 1.5, 10.0]


def test_public_adapter_bounds_order_book_depth(adapter):
    result = adapter.read(
        "public_market_data.read",
        {"operation": "order_book", "symbol": "BTC/USDT", "limit": 10},
        timeout_seconds=4,
    )
    assert result["bids"] == [[9.9, 2.0]]
    assert result["asks"] == [[10.1, 3.0]]


@pytest.mark.parametrize("payload", [
    {"operation": "create_order", "symbol": "BTC/USDT"},
    {"operation": "fetch_balance", "symbol": "BTC/USDT"},
    {"operation": "cancel_order", "symbol": "BTC/USDT"},
])
def test_private_and_mutating_operations_are_not_exposed(adapter, payload):
    with pytest.raises(module.PublicExchangeAdapterError, match="operation_not_allowed"):
        adapter.read("public_market_data.read", payload, timeout_seconds=3)


def test_unknown_capability_is_rejected(adapter):
    with pytest.raises(module.PublicExchangeAdapterError, match="capability_not_supported"):
        adapter.read("balances.read", {"operation": "ticker", "symbol": "BTC/USDT"}, timeout_seconds=3)


@pytest.mark.parametrize("payload", [
    {"operation": "ticker", "symbol": "../../account"},
    {"operation": "ohlcv", "symbol": "BTC/USDT", "timeframe": "1s", "limit": 10},
    {"operation": "ohlcv", "symbol": "BTC/USDT", "timeframe": "1h", "limit": 501},
    {"operation": "order_book", "symbol": "BTC/USDT", "limit": 1000},
])
def test_invalid_symbols_timeframes_and_limits_fail_closed(adapter, payload):
    with pytest.raises(module.PublicExchangeAdapterError):
        adapter.read("public_market_data.read", payload, timeout_seconds=3)


def test_factory_supports_multiple_ccxt_venues(monkeypatch):
    monkeypatch.setattr(module.ccxt, "exchanges", ["binance", "okx", "coinbase"])
    monkeypatch.setattr(module.ccxt, "binance", FakeExchange, raising=False)
    monkeypatch.setattr(module.ccxt, "okx", FakeExchange, raising=False)
    manifest, instance = module.build_public_exchange_connector("okx")
    assert manifest.provider_id == "ccxt.okx.spot"
    assert manifest.capabilities == frozenset({"public_market_data.read"})
    assert manifest.requests_per_minute == 12
    assert instance.venue == "okx"


def test_factory_rejects_unknown_exchange(monkeypatch):
    monkeypatch.setattr(module.ccxt, "exchanges", ["binance"])
    with pytest.raises(module.PublicExchangeAdapterError, match="unsupported_exchange"):
        module.build_public_exchange_connector("unknown")


def test_public_adapter_reuses_existing_radar_client_and_lock(adapter):
    from threading import Lock

    existing_client = adapter._client
    shared_lock = Lock()
    manifest, shared_adapter = module.build_public_exchange_connector(
        "binance",
        timeout_ms=5000,
        client=existing_client,
        lock=shared_lock,
    )

    assert manifest.provider_id == "ccxt.binance.spot"
    assert shared_adapter._client is existing_client
    assert shared_adapter._lock is shared_lock
    result = shared_adapter.read(
        "public_market_data.read",
        {"operation": "ticker", "symbol": "BTC/USDT"},
        timeout_seconds=5,
    )
    assert result["venue"] == "binance"
    assert existing_client.calls[-1] == ("ticker", "BTC/USDT")


@pytest.mark.parametrize("rate_limit", [0, -1, 121, "invalid"])
def test_factory_rejects_unsafe_public_request_rate(rate_limit, monkeypatch):
    monkeypatch.setattr(module.ccxt, "exchanges", ["binance"])
    monkeypatch.setattr(module.ccxt, "binance", FakeExchange, raising=False)
    with pytest.raises(module.PublicExchangeAdapterError, match="invalid_rate_limit"):
        module.build_public_exchange_connector(
            "binance", requests_per_minute=rate_limit
        )


def test_public_connector_factory_default_rate_limit_is_enforced(adapter):
    from threading import Lock

    from PC_ENGINE.core.connector_runtime import ConnectorRegistry

    manifest, public_adapter = module.build_public_exchange_connector(
        "binance",
        client=adapter._client,
        lock=Lock(),
    )
    registry = ConnectorRegistry()
    grants = frozenset({"public_market_data.read"})
    registry.register(
        manifest,
        public_adapter,
        owner_grants=grants,
        provider_verified=grants,
    )

    results = [
        registry.execute_read(
            "ccxt.binance.spot",
            "public_market_data.read",
            {"operation": "ticker", "symbol": "BTC/USDT"},
        )
        for _ in range(13)
    ]

    assert sum(result.ok for result in results) == 12
    assert sum(result.error == "rate_limited" for result in results) == 1
    assert len(adapter._client.calls) == 12
