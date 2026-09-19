from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from typing import Callable

import websocket

from .normalized import MarketEvent, MarketEventFactory


@dataclass(frozen=True)
class WebSocketMarketConfig:
    venue: str
    symbol: str
    url: str


class PublicWebSocketCollector:
    """Observational public-market WebSocket collector."""

    def __init__(self, config: WebSocketMarketConfig, on_event: Callable[[MarketEvent], None]):
        self.config = config
        self.on_event = on_event
        self._stop = threading.Event()
        self._socket: websocket.WebSocketApp | None = None

    def _emit(self, event: MarketEvent) -> None:
        if not self._stop.is_set():
            self.on_event(event)

    def _parse(self, message: str, receive_ns: int) -> list[MarketEvent]:
        payload = json.loads(message)
        venue = self.config.venue
        symbol = self.config.symbol
        events: list[MarketEvent] = []

        if venue == "binance":
            data = payload.get("data", payload)
            event_type = data.get("e")
            ts = data.get("E")
            if event_type in {"trade", "aggTrade"}:
                events.append(MarketEventFactory.create(
                    venue=venue, symbol=symbol, event_type="trade",
                    exchange_ts_ms=ts, provider_ts_ms=ts,
                    sequence=data.get("a"), price=float(data["p"]),
                    volume=float(data["q"]), raw_source="websocket",
                    receive_ns=receive_ns))
            elif event_type == "bookTicker":
                bid, ask = float(data["b"]), float(data["a"])
                events.append(MarketEventFactory.create(
                    venue=venue, symbol=symbol, event_type="ticker",
                    exchange_ts_ms=ts, provider_ts_ms=ts, sequence=data.get("u"),
                    bid=bid, ask=ask, price=(bid + ask) / 2,
                    raw_source="websocket", receive_ns=receive_ns))

        elif venue == "okx":
            channel = payload.get("arg", {}).get("channel")
            for item in payload.get("data", []):
                ts = int(item["ts"]) if item.get("ts") else None
                if channel == "trades":
                    events.append(MarketEventFactory.create(
                        venue=venue, symbol=symbol, event_type="trade",
                        exchange_ts_ms=ts, provider_ts_ms=ts,
                        sequence=int(item["tradeId"]) if item.get("tradeId") else None,
                        price=float(item["px"]), volume=float(item["sz"]),
                        raw_source="websocket", receive_ns=receive_ns))
                elif channel == "tickers":
                    bid = float(item["bidPx"]) if item.get("bidPx") else None
                    ask = float(item["askPx"]) if item.get("askPx") else None
                    last = float(item["last"]) if item.get("last") else None
                    events.append(MarketEventFactory.create(
                        venue=venue, symbol=symbol, event_type="ticker",
                        exchange_ts_ms=ts, provider_ts_ms=ts, price=last,
                        bid=bid, ask=ask, raw_source="websocket",
                        receive_ns=receive_ns))

        elif venue == "coinbase":
            for event in payload.get("events", []):
                for ticker in event.get("tickers", []):
                    bid = float(ticker["best_bid"]) if ticker.get("best_bid") else None
                    ask = float(ticker["best_ask"]) if ticker.get("best_ask") else None
                    last = float(ticker["price"]) if ticker.get("price") else None
                    events.append(MarketEventFactory.create(
                        venue=venue, symbol=symbol, event_type="ticker",
                        price=last, bid=bid, ask=ask, raw_source="websocket",
                        receive_ns=receive_ns))
        return events

    def run_forever(self) -> None:
        def on_message(ws: websocket.WebSocketApp, message: str) -> None:
            receive_ns = time.monotonic_ns()
            try:
                for event in self._parse(message, receive_ns):
                    self._emit(event)
            except (ValueError, TypeError, KeyError, json.JSONDecodeError):
                return

        def on_open(ws: websocket.WebSocketApp) -> None:
            if self.config.venue == "binance":
                return
            if self.config.venue == "okx":
                inst = self.config.symbol.replace("/", "-")
                ws.send(json.dumps({"op": "subscribe", "args": [
                    {"channel": "trades", "instId": inst},
                    {"channel": "tickers", "instId": inst}]}))
            elif self.config.venue == "coinbase":
                product = self.config.symbol.replace("/", "-")
                ws.send(json.dumps({"type": "subscribe", "product_ids": [product], "channel": "ticker"}))

        self._socket = websocket.WebSocketApp(self.config.url, on_open=on_open, on_message=on_message)
        self._socket.run_forever()

    def stop(self) -> None:
        self._stop.set()
        if self._socket is not None:
            self._socket.close()


def default_public_configs(symbol: str) -> list[WebSocketMarketConfig]:
    stream = symbol.replace("/", "").lower()
    return [
        WebSocketMarketConfig("binance", symbol, f"wss://stream.binance.com:9443/ws/{stream}@bookTicker"),
        WebSocketMarketConfig("okx", symbol, "wss://ws.okx.com:8443/ws/v5/public"),
        WebSocketMarketConfig("coinbase", symbol, "wss://advanced-trade-ws.coinbase.com"),
    ]
