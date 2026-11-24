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
from .coinbase_book_sync import CoinbaseL2BookSynchronizer
from .okx_book_sync import OKXBooksSynchronizer
from .orderbook import OrderBookEvent, OrderBookLevel


@dataclass(frozen=True)
class L2WebSocketConfig:
    venue: str
    symbol: str
    url: str


class PublicL2WebSocketCollector:
    """Public L2 collector; Binance and Coinbase can emit synchronized book views."""

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
        self._coinbase_sync: CoinbaseL2BookSynchronizer | None = None
        self._okx_sync: OKXBooksSynchronizer | None = None
        self._health_lock = threading.Lock()
        self._connected = threading.Event()
        self._parse_errors = 0
        self._last_parse_error: str | None = None
        self._raw_callback_errors = 0
        self._last_raw_callback_error: str | None = None
        self._ws_errors = 0
        self._last_ws_error: str | None = None
        self._okx_last_message_monotonic: float | None = None
        self._okx_ping_sent_monotonic: float | None = None
        self._okx_application_pings_sent = 0
        self._okx_application_pongs_received = 0
        self._okx_application_pings_received = 0
        self._okx_application_pongs_sent = 0
        self._okx_heartbeat_timeouts = 0
        if config.venue == "binance" and on_book is not None:
            kwargs = {"on_book": on_book}
            if snapshot_fetcher is not None:
                kwargs["snapshot_fetcher"] = snapshot_fetcher
            self._sync = BinanceSpotBookSynchronizer(config.symbol, **kwargs)
        elif config.venue == "coinbase" and on_book is not None:
            self._coinbase_sync = CoinbaseL2BookSynchronizer(config.symbol, on_book)
        elif config.venue == "okx" and on_book is not None:
            self._okx_sync = OKXBooksSynchronizer(config.symbol, on_book)

    def health_snapshot(self) -> dict:
        with self._health_lock:
            health = {
                "venue": self.config.venue,
                "symbol": self.config.symbol,
                "connected": self._connected.is_set(),
                "parse_errors": self._parse_errors,
                "last_parse_error": self._last_parse_error,
                "raw_callback_errors": self._raw_callback_errors,
                "last_raw_callback_error": self._last_raw_callback_error,
                "websocket_errors": self._ws_errors,
                "last_websocket_error": self._last_ws_error,
                "okx_application_pings_sent": self._okx_application_pings_sent,
                "okx_application_pongs_received": self._okx_application_pongs_received,
                "okx_application_pings_received": self._okx_application_pings_received,
                "okx_application_pongs_sent": self._okx_application_pongs_sent,
                "okx_heartbeat_timeouts": self._okx_heartbeat_timeouts,
            }
        if self._sync is not None:
            health["synchronizer"] = self._sync.health()
        if self._coinbase_sync is not None:
            health["synchronizer"] = self._coinbase_sync.health()
        if self._okx_sync is not None:
            health["synchronizer"] = self._okx_sync.health()
        return health

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
            expected_instrument = symbol.replace("/", "-").upper()
            instrument = arg.get("instId") if isinstance(arg, dict) else None
            if not isinstance(instrument, str) or instrument.upper() != expected_instrument:
                raise ValueError("okx_instrument_mismatch")
            action = payload.get("action", "snapshot")
            if not isinstance(action, str) or action.lower() not in {"snapshot", "update"}:
                raise ValueError("invalid_okx_action")
            # OKX books5 and bbo-tbt publish complete top-of-book snapshots
            # on every push, including messages whose action is "update".
            # Only incremental channels such as books should emit deltas.
            if channel in {"books5", "bbo-tbt"}:
                event_type = "snapshot"
            else:
                event_type = "delta" if action.lower() == "update" else "snapshot"
            items = payload.get("data")
            if not isinstance(items, list):
                raise ValueError("invalid_okx_data")
            if not items:
                raise ValueError("empty_okx_data")
            for item in items:
                if not isinstance(item, dict):
                    raise ValueError("invalid_okx_item")
                ts = int(item["ts"]) if item.get("ts") else None
                raw_sequence = item.get("seqId")
                raw_previous = item.get("prevSeqId")
                if (
                    not isinstance(raw_sequence, int) or isinstance(raw_sequence, bool)
                    or raw_sequence < 0
                ):
                    raise ValueError("invalid_okx_sequence")
                if raw_previous is not None and (
                    not isinstance(raw_previous, int) or isinstance(raw_previous, bool)
                    or raw_previous < -1
                ):
                    raise ValueError("invalid_okx_previous_sequence")
                sequence = raw_sequence
                sequence_start = raw_previous + 1 if raw_previous is not None else None
                bids = self._levels(item.get("bids"))
                asks = self._levels(item.get("asks"))

                if channel == "books" and action.lower() == "update":
                    if raw_previous is None or raw_previous < 0:
                        raise ValueError("invalid_okx_sequence")
                    if sequence == raw_previous:
                        # OKX uses an empty update with seqId == prevSeqId as a
                        # connection heartbeat. It carries no book change and
                        # must not be treated as a sequence gap.
                        if bids or asks:
                            raise ValueError("invalid_okx_heartbeat")
                        events.append(self._event(
                            venue=venue, symbol=symbol, event_type="heartbeat",
                            sequence=sequence, sequence_start=None,
                            exchange_ts_ms=ts, receive_ns=receive_ns,
                            bids=(), asks=(),
                        ))
                        continue
                    if sequence < raw_previous:
                        raise ValueError("invalid_okx_sequence_range")

                events.append(self._event(
                    venue=venue, symbol=symbol, event_type=event_type,
                    sequence=sequence, sequence_start=sequence_start, exchange_ts_ms=ts, receive_ns=receive_ns,
                    bids=bids, asks=asks,
                ))

        elif venue == "coinbase":
            # The subscription is named "level2", while current Advanced Trade
            # market-data envelopes identify the returned channel as "l2_data".
            if payload.get("channel") not in {"level2", "l2_data"}:
                return []
            sequence = payload.get("sequence_num")
            if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 0:
                raise ValueError("invalid_coinbase_sequence")
            items = payload.get("events", [])
            if not isinstance(items, list):
                raise ValueError("invalid_coinbase_events")
            expected_product = symbol.replace("/", "-").upper()
            # sequence_num belongs to the envelope, not each item inside it.
            # Emit one atomic normalized event per envelope so a multi-item
            # message cannot be mistaken for duplicate sequence numbers by the
            # downstream sequence-aware book builder.
            if not items:
                return []
            bids: list[OrderBookLevel] = []
            asks: list[OrderBookLevel] = []
            event_types: set[str] = set()
            timestamps: set[int] = set()
            for item in items:
                if not isinstance(item, dict):
                    raise ValueError("invalid_coinbase_item")
                product_id = item.get("product_id")
                if not isinstance(product_id, str) or product_id.upper() != expected_product:
                    raise ValueError("coinbase_product_mismatch")
                raw_type = str(item.get("type", "")).lower()
                if raw_type == "snapshot":
                    event_types.add("snapshot")
                elif raw_type == "update":
                    event_types.add("delta")
                else:
                    raise ValueError("invalid_coinbase_event_type")
                ts = _iso_ms(item.get("event_time") or payload.get("timestamp"))
                if ts is not None:
                    timestamps.add(ts)
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
            if len(event_types) != 1:
                raise ValueError("mixed_coinbase_event_types")
            if len(timestamps) > 1:
                raise ValueError("mixed_coinbase_timestamps")
            events.append(self._event(
                venue=venue, symbol=symbol, event_type=next(iter(event_types)),
                sequence=sequence, sequence_start=None,
                exchange_ts_ms=next(iter(timestamps), None), receive_ns=receive_ns,
                bids=tuple(bids), asks=tuple(asks),
            ))

        return events

    def process_message(self, message: str) -> None:
        """Parse and dispatch one message while keeping telemetry non-sensitive."""
        receive_ns = time.monotonic_ns()
        try:
            events = self._parse(message, receive_ns)
        except (ValueError, TypeError, KeyError, IndexError, json.JSONDecodeError) as exc:
            # A malformed depth message may conceal a sequence gap. Clear any
            # previously eligible book immediately rather than waiting for TTL.
            if self._sync is not None:
                self._sync.invalidate("parse_error")
            if self._coinbase_sync is not None:
                self._coinbase_sync.invalidate("parse_error")
            if self._okx_sync is not None:
                self._okx_sync.invalidate("parse_error")
            with self._health_lock:
                self._parse_errors += 1
                self._last_parse_error = type(exc).__name__
            return
        for event in events:
            if self._stop.is_set():
                continue
            if self._sync is not None:
                self._sync.on_event(event)
            if self._coinbase_sync is not None:
                self._coinbase_sync.on_event(event)
            if self._okx_sync is not None:
                self._okx_sync.on_event(event)
            # Heartbeats refresh synchronizer liveness but are control frames,
            # not book mutations; do not send them to normalized event storage.
            if event.event_type == "heartbeat":
                continue
            try:
                self.on_event(event)
            except Exception as exc:
                with self._health_lock:
                    self._raw_callback_errors += 1
                    self._last_raw_callback_error = type(exc).__name__

    def _handle_websocket_message(self, ws: websocket.WebSocketApp, message: str) -> None:
        """Handle OKX text heartbeats before parsing market-data JSON."""
        if self.config.venue == "okx" and message in {"ping", "pong"}:
            now = time.monotonic()
            with self._health_lock:
                self._okx_last_message_monotonic = now
                if message == "ping":
                    self._okx_application_pings_received += 1
                else:
                    self._okx_application_pongs_received += 1
                    self._okx_ping_sent_monotonic = None
            if message == "ping":
                try:
                    ws.send("pong")
                except Exception as exc:
                    with self._health_lock:
                        self._ws_errors += 1
                        self._last_ws_error = type(exc).__name__
                    if self._okx_sync is not None:
                        self._okx_sync.invalidate("heartbeat_response_failed")
                    ws.close()
                else:
                    with self._health_lock:
                        self._okx_application_pongs_sent += 1
            return

        if self.config.venue == "okx":
            with self._health_lock:
                self._okx_last_message_monotonic = time.monotonic()
        self.process_message(message)

    def _okx_heartbeat_tick(self, now: float | None = None) -> None:
        """Send the OKX application ping after 20s idle; reconnect if pong misses 10s."""
        if self.config.venue != "okx" or not self._connected.is_set():
            return
        current = time.monotonic() if now is None else now
        socket = self._socket
        action: str | None = None
        with self._health_lock:
            if self._okx_ping_sent_monotonic is not None:
                if current - self._okx_ping_sent_monotonic >= 10.0:
                    self._okx_heartbeat_timeouts += 1
                    self._okx_ping_sent_monotonic = None
                    action = "close"
            elif self._okx_last_message_monotonic is None:
                self._okx_last_message_monotonic = current
            elif current - self._okx_last_message_monotonic >= 20.0:
                self._okx_ping_sent_monotonic = current
                self._okx_application_pings_sent += 1
                action = "ping"
        if socket is None or action is None:
            return
        if action == "close":
            socket.close()
            return
        try:
            socket.send("ping")
        except Exception as exc:
            with self._health_lock:
                self._ws_errors += 1
                self._last_ws_error = type(exc).__name__
            socket.close()

    def _okx_heartbeat_watchdog(self) -> None:
        while not self._stop.wait(1.0):
            self._okx_heartbeat_tick()

    def run_forever(self) -> None:
        if self._sync is not None:
            self._sync.start()
        retry_seconds = 1.0
        heartbeat_thread = None
        if self.config.venue == "okx":
            heartbeat_thread = threading.Thread(
                target=self._okx_heartbeat_watchdog,
                name="vst-okx-ws-heartbeat",
                daemon=True,
            )
            heartbeat_thread.start()
        try:
            while not self._stop.is_set():
                opened_at: list[float] = []

                def on_message(ws: websocket.WebSocketApp, message: str) -> None:
                    self._handle_websocket_message(ws, message)

                def on_open(ws: websocket.WebSocketApp) -> None:
                    opened_at[:] = [time.monotonic()]
                    if self.config.venue == "okx":
                        with self._health_lock:
                            self._okx_last_message_monotonic = time.monotonic()
                            self._okx_ping_sent_monotonic = None
                    self._connected.set()
                    product = self.config.symbol.replace("/", "-").upper()
                    if self.config.venue == "binance":
                        return
                    if self.config.venue == "okx":
                        # Use the incremental channel so sequence continuity is
                        # explicit; books5 snapshots alone cannot prove a gap-free stream.
                        ws.send(json.dumps({"op": "subscribe", "args": [{"channel": "books", "instId": product}]}))
                    elif self.config.venue == "coinbase":
                        ws.send(json.dumps({"type": "subscribe", "product_ids": [product], "channel": "level2"}))

                def on_error(_ws: websocket.WebSocketApp, error: Exception) -> None:
                    with self._health_lock:
                        self._ws_errors += 1
                        self._last_ws_error = type(error).__name__

                def on_close(_ws: websocket.WebSocketApp, _status_code: int | None, _message: str | None) -> None:
                    self._connected.clear()

                self._socket = websocket.WebSocketApp(
                    self.config.url, on_open=on_open, on_message=on_message,
                    on_error=on_error, on_close=on_close,
                )
                try:
                    self._socket.run_forever()
                except Exception as exc:
                    with self._health_lock:
                        self._ws_errors += 1
                        self._last_ws_error = type(exc).__name__
                finally:
                    self._connected.clear()
                if self._stop.is_set():
                    break
                if self._sync is not None:
                    self._sync.connection_lost()
                if self._coinbase_sync is not None:
                    self._coinbase_sync.connection_lost()
                if self._okx_sync is not None:
                    self._okx_sync.connection_lost()
                stable_seconds = time.monotonic() - opened_at[0] if opened_at else 0.0
                if stable_seconds >= 30.0:
                    retry_seconds = 1.0
                if self._stop.wait(retry_seconds):
                    break
                retry_seconds = min(30.0, retry_seconds * 2.0)
        finally:
            if self._sync is not None:
                self._sync.stop()
            if heartbeat_thread is not None and heartbeat_thread is not threading.current_thread():
                heartbeat_thread.join(timeout=2.0)

    def stop(self) -> None:
        self._stop.set()
        if self._socket is not None:
            self._socket.close()
        if self._sync is not None:
            self._sync.stop()
        if self._coinbase_sync is not None:
            self._coinbase_sync.connection_lost()
        if self._okx_sync is not None:
            self._okx_sync.connection_lost()


def _iso_ms(value: str | None) -> int | None:
    if not value:
        return None
    try:
        from datetime import datetime
        return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp() * 1000)
    except (TypeError, ValueError):
        return None


def default_l2_configs(symbol: str) -> list[L2WebSocketConfig]:
    """Build only safe default venue mappings for the requested quote asset.

    BTC/USDT is not interchangeable with Coinbase BTC/USD. Do not manufacture
    a Coinbase product ID for a different quote asset; explicit venue-specific
    product mapping must be supplied by a later, validated configuration path.
    """
    stream = symbol.replace("/", "").lower()
    configs = [
        L2WebSocketConfig("binance", symbol, f"wss://stream.binance.com:9443/ws/{stream}@depth@100ms"),
        L2WebSocketConfig("okx", symbol, "wss://ws.okx.com/ws/v5/public"),
    ]
    parts = symbol.split("/", 1)
    if len(parts) == 2 and parts[0] and parts[1].upper() == "USD":
        configs.append(L2WebSocketConfig("coinbase", symbol, "wss://advanced-trade-ws.coinbase.com"))
    return configs
