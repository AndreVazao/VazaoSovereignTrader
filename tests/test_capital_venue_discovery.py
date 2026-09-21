from __future__ import annotations

from PC_ENGINE.core.capital_venue_discovery import CapitalVenueDiscovery


def test_discovery_fails_closed_without_credentials(monkeypatch):
    for name in (
        "BINANCE_KEY", "BINANCE_PRIVATE", "BINGX_KEY", "BINGX_PRIVATE",
        "OKX_KEY", "OKX_PRIVATE", "BYBIT_KEY", "BYBIT_PRIVATE",
        "COINBASE_KEY", "COINBASE_PRIVATE", "KRAKEN_KEY", "KRAKEN_PRIVATE",
    ):
        monkeypatch.delenv(name, raising=False)

    result = CapitalVenueDiscovery({
        "capital_venue_discovery": {
            "enabled": True,
            "venues": ["binance", "okx", "bybit", "coinbase", "kraken"],
        }
    }).discover()

    assert result["status"] == "NO_READABLE_CAPITAL"
    assert all(v["account_probe"] == "NO_CREDENTIALS" for v in result["venues"])
    assert all("secret" not in str(v).lower() for v in result["venues"])


def test_discovery_reports_credentials_without_probing(monkeypatch):
    monkeypatch.setenv("BINANCE_KEY", "key")
    monkeypatch.setenv("BINANCE_PRIVATE", "secret")

    result = CapitalVenueDiscovery({
        "capital_venue_discovery": {
            "enabled": True,
            "venues": ["binance"],
        }
    }).discover(probe_private_balances=False)

    assert result["status"] == "NO_READABLE_CAPITAL"
    assert result["venues"][0]["account_probe"] == "CREDENTIALS_PRESENT"
    assert result["venues"][0]["quote_cash"] == {}


def test_positive_balance_parser():
    result = CapitalVenueDiscovery({})._positive_balances({
        "total": {"USDT": "125.50", "BTC": "0.0", "ETH": 2, "BAD": "x"}
    })
    assert result == {"USDT": 125.5, "ETH": 2.0}
