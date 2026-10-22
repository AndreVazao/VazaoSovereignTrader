from __future__ import annotations

import json
import math
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Callable

import websocket

from .binance_book_sync import BinanceSpotBookSynchronizer
from .orderbook import OrderBookEvent, OrderBookLevel


@dataclass(frozen=True)
class L2WebSocketConfig:
    venue: str
    symbol: str
    url: str


class PublicL2WebSocketCollector:
    """Public L2 collector; Binance additionally emits a synchronized book view."""

    def __init__(
        self,
        config: L2WebSocketConfig,
        on_event: Callable[[OrderBookEvent], None],
        on_book: Callable[[object], None] | None = None,
        snapshot_fetcher: Callable | None = None,
    ):
        self.config = config
        self.on_event = on_event
        self._stop = threading.Event()
        self._socket: websocket.WebSocketApp | None = None
        self._sync: BinanceSpotBookSynchronizer | None = None
        if config.venue == "binance" and on_book is not None:
            kwargs = {"on_book": on_book}
            if snapshot_fetcher is not None:
                kwargs["snapshot_fetcher"] = snapshot_fetcher
            self._sync = BinanceSpotBookSynchronizer(config.symbol, **kwargs)

    @staticmethod
    def _levels(rows: list | tuple | None) -> tuple[OrderBookLevel, ...]:
        if rows is None:
            return ()
        if not isinstance(rows, (list, tuple)):
            raise ValueError("invalid_levels_container")
        result: list[OrderBookLevel] = []
        for row in rows:
            if isinstance(row, dict):
                price_raw, quantity_raw = row.get("price"), row.get("quantity")
            elif isinstance(row, (list, tuple)) and len(row) >= 2:
                price_raw, quantity_raw = row[0], row[1]
            else:
                raise ValueError("invalid_level_shape")
            try:
                price, quantity = float(price_raw), float(quantity_raw)
            except (TypeError, ValueError, OverflowError) as exc:
                raise ValueError("invalid_level_number") from exc
            if not math.isfinite(price) or price <= 0 or not math.isfinite(quantity) or quantity < 0:
                raise ValueError("invalid_level_value")
            result.append(OrderBookLevel(price, quantity))
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
            sequence_start=sequence_start,
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
        if not isinstance(payload, dict):
            raise ValueError("invalid_payload")
        venue, symbol = self.config.venue, self.config.symbol
        events: list[OrderBookEvent] = []

        if venue == "binance":
            data = payload.get("data", payload)
            if not isinstance(data, dict) or data.get("e") != "depthUpdate":
                return []
            ts = data.get("E")
            if ts is not None and (not isinstance(ts, int) or isinstance(ts, bool) or ts < 0):
                raise ValueError("invalid_exchange_timestamp")
            for key in ("U", "u"):
                if not isinstance(data.get(key), int) or isinstance(data.get(key), bool):
                    raise ValueError("invalid_binance_sequence")
            if data["U"] < 0 or data["u"] < 0 or data["U"] > data["u"]:
                raise ValueError("invalid_binance_sequence_range")
            events.append(self._event(
                venue=venue, symbol=symbol, event_type="delta",
                sequence=data["u"], sequence_start=data["U"], exchange_ts_ms=ts, receive_ns=receive_ns,
                bids=self._levels(data.get("b")), asks=self._levels(data.get("a")),
            ))

        elif venue == "okx":
            arg = payload.get("arg")
            channel = arg.get("channel") if isinstance(arg, dict) else None
            if channel not in {"books", "books5", "bbo-tbt"}:
                return []
            action = str(payload.get("action", "snapshot")).lower()
            event_type = "delta" if action == "update" else "snapshot"
            items = payload.get("data", [])
            if not isinstance(items, list):
                raise ValueError("invalid_okx_data")
            for item in items:
                if not isinstance(item, dict):
                    raise ValueError("invalid_okx_item")
                ts = int(item["ts"]) if item.get("ts") else None
                sequence = int(item["seqId"]) if item.get("seqId") is not None else None
                sequence_start = int(item["prevSeqId"]) + 1 if item.get("prevSeqId") is not None else None
                events.append(self._event(
                    venue=venue, symbol=symbol, event_type=event_type,
                    sequence=sequence, sequence_start=sequence_start, exchange_ts_ms=ts, receive_ns=receive_ns,
                    bids=self._levels(item.get("bids")), asks=self._levels(item.get("asks")),
                ))

        elif venue == "coinbase":
            if payload.get("channel") != "level2":
                return []
            items = payload.get("events", [])
            if not isinstance(items, list):
                raise ValueError("invalid_coinbase_events")
            for item in items:
                if not isinstance(item, dict):
                    raise ValueError("invalid_coinbase_item")
                event_type = "snapshot" if str(item.get("type", "")).lower() == "snapshot" else "delta"
                ts = _iso_ms(item.get("event_time"))
                bids: list[OrderBookLevel] = []
                asks: list[OrderBookLevel] = []
                updates = item.get("updates", [])
                if not isinstance(updates, list):
                    raise ValueError("invalid_coinbase_updates")
                for update in updates:
                    if not isinstance(update, dict):
                        raise ValueError("invalid_coinbase_update")
                    try:
                        level = OrderBookLevel(float(update["price_level"]), float(update["new_quantity"]))
                    except (KeyError, TypeError, ValueError, OverflowError) as exc:
                        raise ValueError("invalid_coinbase_level") from exc
                    if not math.isfinite(level.price) or level.price <= 0 or not math.isfinite(level.quantity) or level.quantity < 0:
                        raise ValueError("invalid_coinbase_level")
                    side = str(update.get("side", "")).upper()
                    if side == "BID":
                        bids.append(level)
                    elif side in {"ASK", "OFFER"}:
                        asks.append(level)
                    else:
                        raise ValueError("invalid_coinbase_side")
                events.append(self._event(
                    venue=venue, symbol=symbol, event_type=event_type,
                    sequence=None, sequence_start=None, exchange_ts_ms=ts, receive_ns=receive_ns,
                    bids=tuple(bids), asks=tuple(asks),
                ))

        return events

    def run_forever(self) -> None:
        if self._sync is not None:
            self._sync.start()

        def on_message(_ws: websocket.WebSocketApp, message: str) -> None:
            receive_ns = time.monotonic_ns()
            try:
                for event in self._parse(message, receive_ns):
                    if self._stop.is_set():
                        continue
                    self.on_event(event)
                    if self._sync is not None:
                        self._sync.on_event(event)
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
        try:
            self._socket.run_forever()
        finally:
            if self._sync is not None:
                self._sync.stop()

    def stop(self) -> None:
        self._stop.set()
        if self._socket is not None:
            self._socket.close()
        if self._sync is not None:
            self._sync.stop()


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
        L2WebSocketConfig("okx", symbol, "wss://ws.okx.com/ws/v5/public"),
        L2WebSocketConfig("coinbase", symbol, "wss://advanced-trade-ws.coinbase.com"),
    ]
