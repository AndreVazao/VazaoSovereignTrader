from __future__ import annotations

import threading
from unittest.mock import patch

from PC_ENGINE.exchanges.ccxt_client import CcxtExchangeClient


def test_prepare_public_markets_skips_network_when_already_cancelled():
    calls = []

    class FakeClient:
        markets = None

        def __init__(self, _options):
            pass

        def load_markets(self):
            calls.append("load")

    with patch("PC_ENGINE.exchanges.ccxt_client.ccxt.binance", FakeClient):
        exchange = CcxtExchangeClient("binance", "", "", paper=True)

    stop = threading.Event()
    stop.set()
    assert exchange.prepare_public_markets(stop) is False
    assert calls == []


def test_prepare_public_markets_observes_cancellation_after_inflight_metadata_request():
    calls = []
    stop = threading.Event()

    class FakeClient:
        markets = None

        def __init__(self, _options):
            pass

        def load_markets(self):
            calls.append("load")
            stop.set()
            return {"BTC/USDT": {}}

    with patch("PC_ENGINE.exchanges.ccxt_client.ccxt.binance", FakeClient):
        exchange = CcxtExchangeClient("binance", "", "", paper=True)

    assert exchange.prepare_public_markets(stop) is False
    assert calls == ["load"]
    stop.clear()
    assert exchange.prepare_public_markets(stop) is True
    assert calls == ["load"]


def test_prepare_public_markets_loads_once_under_repeated_collector_calls():
    calls = []

    class FakeClient:
        markets = None

        def __init__(self, _options):
            pass

        def load_markets(self):
            calls.append("load")
            self.markets = {"BTC/USDT": {}}
            return self.markets

    with patch("PC_ENGINE.exchanges.ccxt_client.ccxt.binance", FakeClient):
        exchange = CcxtExchangeClient("binance", "", "", paper=True)

    assert exchange.prepare_public_markets() is True
    assert exchange.prepare_public_markets() is True
    assert calls == ["load"]
