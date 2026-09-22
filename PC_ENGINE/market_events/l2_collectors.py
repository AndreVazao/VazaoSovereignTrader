from __future__ import annotations

import json
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Callable

import websocket

from .orderbook import OrderBookEvent, OrderBookLevel


@dataclass(frozen=True)
class L2WebSocketConfig:
    venue: str
    symbol: str
    url: str


class PublicL2WebSocketCollector:
    """Public L2 collector for Binance, OKX and Coinbase Advanced Trade."""

    def __init__(self, config: L2WebSocketConfig, on_event: Callable[[OrderBookEvent], None]):
        self.config = config
        self.on_event = on_event
        self._stop = threading.Event()
        self._socket: websocket.WebSocketApp | None = None

    @staticmethod
    def _levels(rows: list | tuple | None) -> tuple[OrderBookLevel, ...]:
        result: list[OrderBookLevel] = []
        for row in rows or []:
            try:
                if isinstance(row, dict):
                    price = float(row.get("price"))
                    quantity = float(row.get("quantity"))
                else:
                    price = float(row[0])
                    quantity = float(row[1])
                if price > 0 and quantity >= 0:
                    result.append(OrderBookLevel(price, quantity))
            except (TypeError, ValueError, IndexError):
                continue
        return tuple(result)

    @staticmethod
    def _event(*, venue: str, symbol: str, event_type: str,
               sequence: int | None, sequence_start: int | None, exchange_ts_ms: int | None,
               receive_ns: int, bids: tuple[OrderBookLevel, ...],
               asks: tuple[OrderBookLevel, ...]) -> OrderBookEvent:
        return OrderBookEvent(
            event_id=uuid.uuid4().hex,
            venue=venue,
            symbol=symbol,
            event_type=event_type,
            sequence=sequence,
            provider_ts_ms=exchange_ts_ms,
            exchange_ts_ms=exchange_ts_ms,
            local_receive_ns=receive_ns,
            local_receive_wall_ns=time.time_ns(),
            bids=bids,
            asks=asks,
            raw_source="websocket",
        )

    def _parse(self, message: str, receive_ns: int) -> list[OrderBookEvent]:
        payload = json.loads(message)
        venue = self.config.venue
        symbol = self.config.symbol
        events: list[OrderBookEvent] = []

        if venue == "binance":
            data = payload.get("data", payload)
            if data.get("e") != "depthUpdate":
                return []
            ts = int(data["E"]) if data.get("E") is not None else None
            sequence = int(data["u"]) if data.get("u") is not None else None
            sequence_start = int(data["U"]) if data.get("U") is not None else None
            events.append(self._event(
                venue=venue, symbol=symbol, event_type="delta",
                sequence=sequence, sequence_start=sequence_start, exchange_ts_ms=ts, receive_ns=receive_ns,
                bids=self._levels(data.get("b")), asks=self._levels(data.get("a")),
            ))

        elif venue == "okx":
            channel = payload.get("arg", {}).get("channel")
            if channel not in {"books", "books5", "bbo-tbt"}:
                return []
            event_type = "delta" if str(payload.get("action", "snapshot")).lower() == "update" else "snapshot"
            for item in payload.get("data", []):
                ts = int(item["ts"]) if item.get("ts") else None
                sequence = int(item["seqId"]) if item.get("seqId") is not None else None
                sequence_start = int(item["prevSeqId"]) + 1 if item.get("prevSeqId") is not None else None
                events.append(self._event(
                    venue=venue, symbol=symbol, event_type=event_type,
                    sequence=sequence, sequence_start=sequence_start, exchange_ts_ms=ts, receive_ns=receive_ns,
                    bids=self._levels(item.get("bids")),
                    asks=self._levels(item.get("asks")),
                ))

        elif venue == "coinbase":
            if payload.get("channel") != "level2":
                return []
            for item in payload.get("events", []):
                event_type = "snapshot" if str(item.get("type", "")).lower() == "snapshot" else "delta"
                ts = _iso_ms(item.get("event_time"))
                bids: list[OrderBookLevel] = []
                asks: list[OrderBookLevel] = []
                for update in item.get("updates", []):
                    try:
                        level = OrderBookLevel(float(update["price_level"]), float(update["new_quantity"]))
                    except (KeyError, TypeError, ValueError):
                        continue
                    side = str(update.get("side", "")).upper()
                    if side == "BID":
                        bids.append(level)
                    elif side in {"ASK", "OFFER"}:
                        asks.append(level)
                events.append(self._event(
                    venue=venue, symbol=symbol, event_type=event_type,
                    sequence=None, sequence_start=None, exchange_ts_ms=ts, receive_ns=receive_ns,
                    bids=tuple(bids), asks=tuple(asks),
                ))

        return events

    def run_forever(self) -> None:
        def on_message(_ws: websocket.WebSocketApp, message: str) -> None:
            receive_ns = time.monotonic_ns()
            try:
                for event in self._parse(message, receive_ns):
                    if not self._stop.is_set():
                        self.on_event(event)
            except (ValueError, TypeError, KeyError, IndexError, json.JSONDecodeError):
                return

        def on_open(ws: websocket.WebSocketApp) -> None:
            product = self.config.symbol.replace("/", "-").upper()
            if self.config.venue == "binance":
                return
            if self.config.venue == "okx":
                ws.send(json.dumps({"op": "subscribe", "args": [{"channel": "books5", "instId": product}]}))
            elif self.config.venue == "coinbase":
                ws.send(json.dumps({"type": "subscribe", "product_ids": [product], "channel": "level2"}))

        self._socket = websocket.WebSocketApp(self.config.url, on_open=on_open, on_message=on_message)
        self._socket.run_forever()

    def stop(self) -> None:
        self._stop.set()
        if self._socket is not None:
            self._socket.close()


def _iso_ms(value: str | None) -> int | None:
    if not value:
        return None
    try:
        from datetime import datetime
        return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp() * 1000)
    except (TypeError, ValueError):
        return None


def default_l2_configs(symbol: str) -> list[L2WebSocketConfig]:
    stream = symbol.replace("/", "").lower()
    return [
        L2WebSocketConfig("binance", symbol, f"wss://stream.binance.com:9443/ws/{stream}@depth@100ms"),
        L2WebSocketConfig("okx", symbol, "wss://ws.okx.com:8443/ws/v5/public"),
        L2WebSocketConfig("coinbase", symbol, "wss://advanced-trade-ws.coinbase.com"),
    ]
