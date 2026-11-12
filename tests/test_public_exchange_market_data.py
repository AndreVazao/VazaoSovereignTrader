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
    assert instance.venue == "okx"


def test_factory_rejects_unknown_exchange(monkeypatch):
    monkeypatch.setattr(module.ccxt, "exchanges", ["binance"])
    with pytest.raises(module.PublicExchangeAdapterError, match="unsupported_exchange"):
        module.build_public_exchange_connector("unknown")
