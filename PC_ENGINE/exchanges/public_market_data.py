from __future__ import annotations

import math
import re
from threading import Lock
from typing import Any, Mapping

import ccxt

from PC_ENGINE.core.platform_connectors import (
    AccessMethod,
    ConnectorCategory,
    ConnectorHealth,
    ConnectorManifest,
)

_SYMBOL = re.compile(r"^[A-Z0-9]{2,20}/[A-Z0-9]{2,20}$")
_TIMEFRAME = re.compile(r"^(1m|3m|5m|15m|30m|1h|2h|4h|6h|12h|1d|3d|1w)$")
_ALLOWED_OPERATIONS = frozenset({"ticker", "ohlcv", "order_book"})


class PublicExchangeAdapterError(ValueError):
    """Raised for invalid or unsupported public market-data requests."""


class CcxtPublicMarketDataAdapter:
    """Credential-free CCXT adapter exposing only bounded public market reads.

    It deliberately constructs an unauthenticated CCXT client and never exposes
    the client object. No private/account/order method is reachable through the
    request contract. Use official exchange endpoints through CCXT's public API.
    """

    def __init__(
        self,
        venue: str,
        *,
        timeout_ms: int = 8_000,
        client: Any | None = None,
        lock: Any | None = None,
    ) -> None:
        venue_id = str(venue or "").strip().lower()
        if venue_id not in ccxt.exchanges:
            raise PublicExchangeAdapterError("unsupported_exchange")
        if not 1_000 <= int(timeout_ms) <= 60_000:
            raise PublicExchangeAdapterError("invalid_timeout")
        exchange_type = getattr(ccxt, venue_id, None)
        if exchange_type is None:
            raise PublicExchangeAdapterError("unsupported_exchange")
        self.provider_id = f"ccxt.{venue_id}.spot"
        self.venue = venue_id
        # Production runtime may inject the already-public MarketRadar client.
        # Sharing it avoids duplicate CCXT sessions on constrained PCs.
        self._client = client if client is not None else exchange_type({
            "enableRateLimit": True,
            "timeout": int(timeout_ms),
            "options": {"defaultType": "spot"},
        })
        self._lock = lock if lock is not None else Lock()

    @staticmethod
    def _symbol(request: Mapping[str, object]) -> str:
        symbol = request.get("symbol")
        if not isinstance(symbol, str):
            raise PublicExchangeAdapterError("symbol_required")
        normalized = symbol.strip().upper()
        if not _SYMBOL.fullmatch(normalized):
            raise PublicExchangeAdapterError("invalid_symbol")
        return normalized

    @staticmethod
    def _number(value: object) -> float | None:
        if value is None:
            return None
        try:
            result = float(value)
        except (TypeError, ValueError, OverflowError):
            return None
        return result if math.isfinite(result) else None

    def read(
        self,
        capability: str,
        request: Mapping[str, object],
        *,
        timeout_seconds: float,
    ) -> Mapping[str, object]:
        if capability != "public_market_data.read":
            raise PublicExchangeAdapterError("capability_not_supported")
        if not isinstance(request, Mapping):
            raise PublicExchangeAdapterError("invalid_request")
        operation = request.get("operation")
        if not isinstance(operation, str) or operation not in _ALLOWED_OPERATIONS:
            raise PublicExchangeAdapterError("operation_not_allowed")
        symbol = self._symbol(request)
        timeout = float(timeout_seconds)
        if not math.isfinite(timeout) or not 0.1 <= timeout <= 60:
            raise PublicExchangeAdapterError("invalid_timeout")

        # CCXT stores timeout on the client. Serialize calls so a concurrent
        # request cannot change another request's timeout while it is in flight.
        with self._lock:
            self._client.timeout = max(100, int(timeout * 1000))
            if operation == "ticker":
                raw = self._client.fetch_ticker(symbol)
                return {
                    "venue": self.venue,
                    "symbol": symbol,
                    "operation": "ticker",
                    "timestamp": self._number(raw.get("timestamp")),
                    "last": self._number(raw.get("last")),
                    "bid": self._number(raw.get("bid")),
                    "ask": self._number(raw.get("ask")),
                    "high": self._number(raw.get("high")),
                    "low": self._number(raw.get("low")),
                    "base_volume": self._number(raw.get("baseVolume")),
                    "quote_volume": self._number(raw.get("quoteVolume")),
                }
            if operation == "ohlcv":
                timeframe = request.get("timeframe", "1h")
                if not isinstance(timeframe, str) or not _TIMEFRAME.fullmatch(timeframe):
                    raise PublicExchangeAdapterError("invalid_timeframe")
                limit = request.get("limit", 100)
                if type(limit) is not int or not 1 <= limit <= 500:
                    raise PublicExchangeAdapterError("invalid_limit")
                candles = self._client.fetch_ohlcv(
                    symbol, timeframe=timeframe, limit=limit
                )
                normalized = []
                for candle in candles[:limit]:
                    if not isinstance(candle, (list, tuple)) or len(candle) < 6:
                        continue
                    values = [self._number(item) for item in candle[:6]]
                    if any(item is None for item in values):
                        continue
                    normalized.append(values)
                return {
                    "venue": self.venue,
                    "symbol": symbol,
                    "operation": "ohlcv",
                    "timeframe": timeframe,
                    "candles": normalized,
                }
            depth = request.get("limit", 20)
            if type(depth) is not int or not 1 <= depth <= 50:
                raise PublicExchangeAdapterError("invalid_limit")
            book = self._client.fetch_order_book(symbol, limit=depth)
            def levels(name: str) -> list[list[float]]:
                result = []
                for level in book.get(name, [])[:depth]:
                    if not isinstance(level, (list, tuple)) or len(level) < 2:
                        continue
                    price, amount = self._number(level[0]), self._number(level[1])
                    if price is not None and amount is not None and price > 0 and amount >= 0:
                        result.append([price, amount])
                return result
            return {
                "venue": self.venue,
                "symbol": symbol,
                "operation": "order_book",
                "timestamp": self._number(book.get("timestamp")),
                "bids": levels("bids"),
                "asks": levels("asks"),
            }


def build_public_exchange_connector(
    venue: str,
    *,
    timeout_ms: int = 8_000,
    client: Any | None = None,
    lock: Any | None = None,
    requests_per_minute: int = 12,
) -> tuple[ConnectorManifest, CcxtPublicMarketDataAdapter]:
    """Build a provider-neutral manifest and a public-only adapter for any CCXT venue."""
    try:
        rate_limit = int(requests_per_minute)
    except (TypeError, ValueError, OverflowError):
        raise PublicExchangeAdapterError("invalid_rate_limit") from None
    if not 1 <= rate_limit <= 120:
        raise PublicExchangeAdapterError("invalid_rate_limit")
    adapter = CcxtPublicMarketDataAdapter(
        venue, timeout_ms=timeout_ms, client=client, lock=lock
    )
    manifest = ConnectorManifest(
        provider_id=adapter.provider_id,
        display_name=f"{adapter.venue.upper()} public market data",
        category=ConnectorCategory.MARKET_DATA,
        access_method=AccessMethod.OFFICIAL_API,
        capabilities=frozenset({"public_market_data.read"}),
        requests_per_minute=rate_limit,
        request_timeout_seconds=min(60.0, max(0.1, timeout_ms / 1000)),
        health=ConnectorHealth.AVAILABLE,
        adapter_version="1",
    )
    return manifest, adapter
