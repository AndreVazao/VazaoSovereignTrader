from __future__ import annotations

import os
import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable

from PC_ENGINE.exchanges.ccxt_client import CcxtExchangeClient


@dataclass(frozen=True)
class CapitalVenue:
    venue_id: str
    display_name: str
    enabled: bool
    credentials_configured: bool
    account_probe: str
    quote_cash: Dict[str, float]
    nonzero_assets: Dict[str, float]
    observed_at_ms: int
    error: str = ""


SUPPORTED_CAPITAL_VENUES: dict[str, dict[str, Any]] = {
    "binance": {"display_name": "Binance", "key_env": "BINANCE_KEY", "private_env": "BINANCE_PRIVATE", "quotes": ["USDT", "USDC", "EUR"]},
    "bingx": {"display_name": "BingX", "key_env": "BINGX_KEY", "private_env": "BINGX_PRIVATE", "quotes": ["USDT", "USDC"]},
    "okx": {"display_name": "OKX", "key_env": "OKX_KEY", "private_env": "OKX_PRIVATE", "quotes": ["USDT", "USDC", "EUR"]},
    "bybit": {"display_name": "Bybit", "key_env": "BYBIT_KEY", "private_env": "BYBIT_PRIVATE", "quotes": ["USDT", "USDC", "EUR"]},
    "coinbase": {"display_name": "Coinbase", "key_env": "COINBASE_KEY", "private_env": "COINBASE_PRIVATE", "quotes": ["USDC", "USD", "EUR"]},
    "kraken": {"display_name": "Kraken", "key_env": "KRAKEN_KEY", "private_env": "KRAKEN_PRIVATE", "quotes": ["USD", "EUR", "USDT"]},
}


class CapitalVenueDiscovery:
    """Read-only discovery of where an owner's capital is available.

    This component never creates, cancels or transfers orders/funds. Credentials are
    read only from environment variables and are never returned in snapshots.
    """

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.last_snapshot: dict[str, Any] = {
            "status": "NOT_RUN",
            "venues": [],
            "observed_at_ms": 0,
        }

    @staticmethod
    def _configured(key_env: str, private_env: str) -> bool:
        return bool(os.getenv(key_env, "").strip() and os.getenv(private_env, "").strip())

    @staticmethod
    def _positive_balances(balance: dict[str, Any]) -> dict[str, float]:
        total = balance.get("total", {}) or {}
        out: dict[str, float] = {}
        for asset, value in total.items():
            try:
                amount = float(value or 0.0)
            except (TypeError, ValueError):
                continue
            if amount > 0:
                out[str(asset).upper()] = amount
        return out

    def discover(self, probe_private_balances: bool = True) -> dict[str, Any]:
        cfg = dict(self.config.get("capital_venue_discovery", {}))
        configured_venues = cfg.get("venues") or list(SUPPORTED_CAPITAL_VENUES)
        results: list[dict[str, Any]] = []
        now = int(time.time() * 1000)

        for venue_id in configured_venues:
            spec = SUPPORTED_CAPITAL_VENUES.get(str(venue_id).lower())
            if spec is None:
                continue
            venue_id = str(venue_id).lower()
            enabled = bool(cfg.get("enabled", True))
            key_env = str(spec["key_env"])
            private_env = str(spec["private_env"])
            credentials = self._configured(key_env, private_env)

            if not enabled:
                results.append(asdict(CapitalVenue(
                    venue_id, spec["display_name"], False, credentials, "DISABLED", {}, {}, now
                )))
                continue

            if not credentials:
                results.append(asdict(CapitalVenue(
                    venue_id, spec["display_name"], True, False, "NO_CREDENTIALS", {}, {}, now
                )))
                continue

            if not probe_private_balances:
                results.append(asdict(CapitalVenue(
                    venue_id, spec["display_name"], True, True, "CREDENTIALS_PRESENT", {}, {}, now
                )))
                continue

            try:
                client = CcxtExchangeClient(
                    name=venue_id,
                    key_env=key_env,
                    private_env=private_env,
                    paper=False,
                )
                balance = client.fetch_balance()
                totals = self._positive_balances(balance)
                quotes = {
                    quote: float(totals.get(quote, 0.0))
                    for quote in spec["quotes"]
                    if float(totals.get(quote, 0.0)) > 0
                }
                results.append(asdict(CapitalVenue(
                    venue_id, spec["display_name"], True, True, "BALANCE_OK",
                    quotes, totals, now
                )))
            except Exception as exc:
                # Do not leak exchange error payloads into the dashboard by default.
                results.append(asdict(CapitalVenue(
                    venue_id, spec["display_name"], True, True, "PRIVATE_UNAVAILABLE",
                    {}, {}, now, error=type(exc).__name__
                )))

        ready = [v for v in results if v["account_probe"] == "BALANCE_OK" and v["quote_cash"]]
        status = "READY" if ready else "NO_READABLE_CAPITAL"
        self.last_snapshot = {
            "status": status,
            "venues": results,
            "readable_venues": [v["venue_id"] for v in ready],
            "observed_at_ms": now,
            "read_only": True,
        }
        return dict(self.last_snapshot)

    def snapshot(self) -> dict[str, Any]:
        return dict(self.last_snapshot)
