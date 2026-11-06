from __future__ import annotations

import json
from pathlib import Path

from PC_ENGINE.radar.public_market_data_bootstrap import bootstrap_public_market_data


class FakeClient:
    def __init__(self, name: str) -> None:
        self.name = name
        self.closed = False

    def load_markets(self):
        return {}

    def fetch_ticker(self, symbol: str):
        return {"last": 100.0, "timestamp": 1_700_000_000_000}

    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int):
        base = 1_700_000_000_000
        return [
            [base + index * 60_000, 100.0, 101.0, 99.0, 100.5, 10.0]
            for index in range(60)
        ]

    def close(self):
        self.closed = True


def test_bootstrap_is_public_only_and_writes_ready_manifest(tmp_path: Path) -> None:
    clients = {}

    def factory(name: str):
        clients[name] = FakeClient(name)
        return clients[name]

    report = bootstrap_public_market_data(
        exchanges=["binance", "okx"],
        symbols=["BTC/USDT"],
        data_dir=tmp_path,
        client_factory=factory,
    )

    assert report["status"] == "READY"
    assert report["public_only"] is True
    assert report["private_credentials_used"] is False
    assert report["orders_submitted"] is False
    assert report["execution_authorized"] is False
    assert report["ready_venues"] == 2
    assert all(client.closed for client in clients.values())

    saved = json.loads((tmp_path / "market_data_bootstrap.json").read_text(encoding="utf-8"))
    assert saved["status"] == "READY"
    assert saved["venues"][0]["symbols"]["BTC/USDT"]["status"] == "READY"


def test_bootstrap_fails_closed_for_invalid_market_data(tmp_path: Path) -> None:
    class BadClient(FakeClient):
        def fetch_ticker(self, symbol: str):
            return {"last": 0, "timestamp": 1_700_000_000_000}

    report = bootstrap_public_market_data(
        exchanges=["binance"],
        symbols=["BTC/USDT"],
        data_dir=tmp_path,
        client_factory=lambda _name: BadClient("bad"),
    )

    assert report["status"] == "DEGRADED"
    assert report["ready_venues"] == 0
    assert report["venues"][0]["symbols"]["BTC/USDT"]["status"] == "FAILED"



class UnavailableClient(FakeClient):
    def fetch_ticker(self, symbol: str):
        raise RuntimeError("simulated public venue outage")


def test_bootstrap_accepts_minimum_ready_venues_and_reports_optional_failures(tmp_path: Path) -> None:
    clients = {}

    def factory(name: str):
        client = FakeClient(name) if name == "binance" else UnavailableClient(name)
        clients[name] = client
        return client

    report = bootstrap_public_market_data(
        exchanges=["binance", "coinbase"],
        symbols=["BTC/USDT"],
        data_dir=tmp_path,
        client_factory=factory,
        require_all_exchanges=False,
        minimum_ready_venues=1,
    )

    assert report["status"] == "READY"
    assert report["readiness_policy"] == "MINIMUM_READY_VENUES"
    assert report["minimum_ready_venues"] == 1
    assert report["ready_venues"] == 1
    assert report["degraded_venues"] == ["coinbase"]
    assert report["all_configured_venues_ready"] is False
    assert report["venues"][1]["status"] == "DEGRADED"
    assert all(client.closed for client in clients.values())

    saved = json.loads((tmp_path / "market_data_bootstrap.json").read_text(encoding="utf-8"))
    assert saved["status"] == "READY"
    assert saved["degraded_venues"] == ["coinbase"]


def test_bootstrap_stays_degraded_when_minimum_ready_venues_is_not_met(tmp_path: Path) -> None:
    report = bootstrap_public_market_data(
        exchanges=["binance", "coinbase"],
        symbols=["BTC/USDT"],
        data_dir=tmp_path,
        client_factory=lambda name: FakeClient(name) if name == "binance" else UnavailableClient(name),
        require_all_exchanges=False,
        minimum_ready_venues=2,
    )

    assert report["status"] == "DEGRADED"
    assert report["ready_venues"] == 1
    assert report["minimum_ready_venues"] == 2
    assert report["degraded_venues"] == ["coinbase"]


def test_bootstrap_rejects_zero_minimum_ready_venues(tmp_path: Path) -> None:
    import pytest

    with pytest.raises(ValueError, match="at least 1"):
        bootstrap_public_market_data(
            exchanges=["binance"],
            symbols=["BTC/USDT"],
            data_dir=tmp_path,
            minimum_ready_venues=0,
            require_all_exchanges=False,
        )
