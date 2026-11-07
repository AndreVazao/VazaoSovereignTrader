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


def test_private_balance_probe_is_disabled_by_default_even_with_credentials(monkeypatch):
    monkeypatch.setenv("BINANCE_KEY", "key")
    monkeypatch.setenv("BINANCE_PRIVATE", "secret")

    def forbidden_client(**kwargs):
        raise AssertionError("private exchange client must not be constructed by default")

    monkeypatch.setattr(
        "PC_ENGINE.core.capital_venue_discovery.CcxtExchangeClient",
        forbidden_client,
    )
    result = CapitalVenueDiscovery({
        "capital_venue_discovery": {"enabled": True, "venues": ["binance"]}
    }).discover()

    assert result["status"] == "NO_READABLE_CAPITAL"
    assert result["venues"][0]["account_probe"] == "CREDENTIALS_PRESENT"
    assert result["venues"][0]["quote_cash"] == {}


def test_config_can_explicitly_enable_private_balance_probe(monkeypatch):
    monkeypatch.setenv("BINANCE_KEY", "key")
    monkeypatch.setenv("BINANCE_PRIVATE", "secret")

    class ReadOnlyClient:
        def __init__(self, **kwargs):
            assert kwargs["paper"] is False

        def fetch_balance(self):
            return {"total": {"USDT": "42", "BTC": "0"}}

    monkeypatch.setattr(
        "PC_ENGINE.core.capital_venue_discovery.CcxtExchangeClient",
        ReadOnlyClient,
    )
    result = CapitalVenueDiscovery({
        "capital_venue_discovery": {
            "enabled": True,
            "probe_private_balances": True,
            "venues": ["binance"],
        }
    }).discover()

    assert result["status"] == "READY"
    assert result["venues"][0]["account_probe"] == "BALANCE_OK"
    assert result["venues"][0]["quote_cash"] == {"USDT": 42.0}


def test_explicit_probe_argument_overrides_disabled_config(monkeypatch):
    monkeypatch.setenv("BINANCE_KEY", "key")
    monkeypatch.setenv("BINANCE_PRIVATE", "secret")

    class ReadOnlyClient:
        def __init__(self, **kwargs):
            pass

        def fetch_balance(self):
            return {"total": {"USDT": "7"}}

    monkeypatch.setattr(
        "PC_ENGINE.core.capital_venue_discovery.CcxtExchangeClient",
        ReadOnlyClient,
    )
    result = CapitalVenueDiscovery({
        "capital_venue_discovery": {
            "enabled": True,
            "probe_private_balances": False,
            "venues": ["binance"],
        }
    }).discover(probe_private_balances=True)

    assert result["status"] == "READY"
    assert result["venues"][0]["quote_cash"] == {"USDT": 7.0}
