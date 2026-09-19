from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Callable
from urllib.request import Request, urlopen

from .orderbook import OrderBookEvent, OrderBookLevel
from .orderbook_builder import OrderBookBuilder, ReconstructedBook


@dataclass(frozen=True)
class BinanceDepthSnapshot:
    symbol: str
    last_update_id: int
    bids: tuple[OrderBookLevel, ...]
    asks: tuple[OrderBookLevel, ...]

    def as_event(self) -> OrderBookEvent:
        return OrderBookEvent(
            event_id=f"binance-snapshot-{self.last_update_id}",
            venue="binance",
            symbol=self.symbol,
            event_type="snapshot",
            sequence=self.last_update_id,
            sequence_start=None,
            provider_ts_ms=None,
            exchange_ts_ms=None,
            local_receive_ns=0,
            local_receive_wall_ns=0,
            bids=self.bids,
            asks=self.asks,
            raw_source="binance-rest-depth",
        )


class BinanceSnapshotClient:
    """Minimal public REST snapshot client; no credentials are required."""

    def __init__(self, base_url: str = "https://api.binance.com/api/v3/depth", timeout_s: float = 5.0):
        self.base_url = base_url
        self.timeout_s = timeout_s

    def fetch(self, symbol: str, limit: int = 1000) -> BinanceDepthSnapshot:
        product = symbol.replace("/", "").upper()
        request = Request(f"{self.base_url}?symbol={product}&limit={int(limit)}", headers={"User-Agent": "VazaoSovereignTrader/1.0"})
        with urlopen(request, timeout=self.timeout_s) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return BinanceDepthSnapshot(
            symbol=symbol,
            last_update_id=int(payload["lastUpdateId"]),
            bids=_levels(payload.get("bids")),
            asks=_levels(payload.get("asks")),
        )


class BinanceL2Bootstrapper:
    """Bootstrap Binance from REST snapshot plus buffered WebSocket deltas."""

    def __init__(self, snapshot_client: BinanceSnapshotClient | None = None):
        self.snapshot_client = snapshot_client or BinanceSnapshotClient()

    def bootstrap(
        self,
        symbol: str,
        buffered_events: list[OrderBookEvent],
        limit: int = 1000,
    ) -> tuple[OrderBookBuilder, ReconstructedBook | None]:
        snapshot = self.snapshot_client.fetch(symbol, limit=limit)
        builder = OrderBookBuilder("binance", symbol)
        book = builder.bootstrap(snapshot.as_event(), buffered_events)
        return builder, book


def _levels(rows: list | None) -> tuple[OrderBookLevel, ...]:
    result: list[OrderBookLevel] = []
    for row in rows or []:
        try:
            price = float(row[0])
            quantity = float(row[1])
        except (TypeError, ValueError, IndexError):
            continue
        if price > 0 and quantity >= 0:
            result.append(OrderBookLevel(price, quantity))
    return tuple(result)


SnapshotFetcher = Callable[[str], BinanceDepthSnapshot]
