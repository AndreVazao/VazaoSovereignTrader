from __future__ import annotations

import json
from collections import OrderedDict
import math
import random
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

import websocket

from PC_ENGINE.radar.latency_edge import LatencyEdgeDetector
from PC_ENGINE.radar.external_source_latency import ExternalSourceLatencyProfiler, SourceLatencyObservation
from PC_ENGINE.radar.external_source_adapter import ExternalMarketObservation, validate_observation


@dataclass(frozen=True)
class MarketEvent:
    exchange: str
    symbol: str
    price: float
    quantity: float
    side: str
    exchange_ts_ms: int
    local_ts_ms: int
    # None until a validated clock-offset model can estimate one-way latency.
    local_receive_latency_ms: int | None
    price_before: float | None = None
    # Venue-native trade identity, when the public feed provides one.
    trade_id: str | None = None


@dataclass(frozen=True)
class LeadLagEvent:
    symbol: str
    leader: str
    follower: str
    direction: str
    leader_exchange_ts_ms: int
    follower_exchange_ts_ms: int
    exchange_lag_ms: int
    leader_receive_ts_ms: int
    follower_receive_ts_ms: int
    receive_lag_ms: int
    leader_move_bps: float
    follower_move_bps: float


class WebSocketMarketRadar:
    """Low-latency public trade collector for the radar observation phase.

    Observation-only: no authentication, private account data or orders.
    Current native public adapters are Binance, Coinbase and OKX spot trades.

    The optional callback is deliberately invoked before disk persistence so
    the Fast Path is not delayed by JSONL I/O on the opportunity tick.
    """

    ENDPOINTS = {
        "binance": "wss://stream.binance.com:9443/stream?streams={streams}",
        "coinbase": "wss://advanced-trade-ws.coinbase.com",
        "okx": "wss://ws.okx.com:8443/ws/v5/public",
    }

    def __init__(self, symbols: list[str], exchanges: list[str] | None = None,
                 data_dir: str | Path = "PC_ENGINE/data/radar",
                 min_move_bps: float = 5.0, lead_window_ms: int = 750,
                 callback: Callable[[MarketEvent], None] | None = None,
                 latency_detector: LatencyEdgeDetector | None = None,
                 external_latency_profiler: ExternalSourceLatencyProfiler | None = None) -> None:
        self.symbols = list(dict.fromkeys(symbols))
        wanted = exchanges or ["binance", "coinbase", "okx"]
        self.exchanges = [x for x in dict.fromkeys(wanted) if x in self.ENDPOINTS]
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.min_move = float(min_move_bps) / 10000.0
        self.lead_window_ms = int(lead_window_ms)
        self.callback = callback
        self.latency_detector = latency_detector or LatencyEdgeDetector(max_lead_ms=self.lead_window_ms)
        self.external_latency_profiler = external_latency_profiler
        self._recent_market_events: dict[str, list[MarketEvent]] = {}
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []
        self._lifecycle_lock = threading.RLock()
        self._stop_lock = threading.Lock()
        self._stopping = False
        self._apps: dict[str, websocket.WebSocketApp] = {}
        self._last_price: dict[tuple[str, str], float] = {}
        # Bounded deduplication protects against replayed trades after reconnect.
        self._seen_trade_ids: OrderedDict[tuple[str, str, str], None] = OrderedDict()
        self._max_seen_trade_ids = 10_000
        self._last_move: dict[tuple[str, str], MarketEvent] = {}
        self._lock = threading.RLock()
        self._events_total = 0
        self._events_by_exchange: dict[str, int] = {}
        self._last_event: dict[str, dict] = {}
        self._connection_state: dict[str, str] = {exchange: "never_connected" for exchange in self.exchanges}
        self._last_connected_ts_ms: dict[str, int] = {}
        self._last_disconnected_ts_ms: dict[str, int] = {}
        self._last_message_ts_ms: dict[str, int] = {}
        # Keep only a safe error category, never raw exception text or URLs.
        self._last_connection_error: dict[str, str] = {}
        self._reconnects: dict[str, int] = {exchange: 0 for exchange in self.exchanges}
        self._errors: dict[str, int] = {exchange: 0 for exchange in self.exchanges}
        self._persistence_errors = 0

    @staticmethod
    def normalize_symbol(symbol: str) -> tuple[str, str]:
        base, quote = symbol.upper().split("/")
        return base, quote

    @staticmethod
    def _now_ms() -> int:
        return time.time_ns() // 1_000_000

    def snapshot(self) -> dict:
        with self._lock:
            now = self._now_ms()
            last = dict(self._last_event)
            return {
                "running": any(thread.is_alive() for thread in self._threads),
                "symbols": list(self.symbols),
                "exchanges": list(self.exchanges),
                "events_total": self._events_total,
                "events_by_exchange": dict(self._events_by_exchange),
                "last_event": last,
                "connection_state": dict(self._connection_state),
                "last_connected_ts_ms": dict(self._last_connected_ts_ms),
                "last_disconnected_ts_ms": dict(self._last_disconnected_ts_ms),
                "last_message_ts_ms": dict(self._last_message_ts_ms),
                "last_connection_error": dict(self._last_connection_error),
                "reconnects": dict(self._reconnects),
                "errors": dict(self._errors),
                "persistence_errors": self._persistence_errors,
                "last_event_age_ms": {
                    exchange: max(0, now - int(row["local_ts_ms"]))
                    for exchange, row in last.items()
                },
                # Trade silence is a data-freshness signal, not proof of a
                # disconnected socket; quiet markets/symbols can be legitimate.
                "trade_freshness": {
                    exchange: (
                        "no_trade_yet" if exchange not in last else
                        "recent_trade" if max(0, now - int(last[exchange]["local_ts_ms"])) <= 30_000 else
                        "no_recent_trade"
                    )
                    for exchange in self.exchanges
                },
                "worker_alive": {
                    exchange: any(
                        thread.name == f"radar-ws-{exchange}" and thread.is_alive()
                        for thread in self._threads
                    )
                    for exchange in self.exchanges
                },
            }

    def start(self) -> None:
        """Start one worker per exchange; repeated calls are idempotent."""
        with self._lifecycle_lock:
            if self._stopping:
                return
            self._threads = [thread for thread in self._threads if thread.is_alive()]
            if self._threads:
                return
            self._stop.clear()
            for exchange in self.exchanges:
                target = getattr(self, f"_run_{exchange}", None)
                if target is None:
                    continue
                thread = threading.Thread(target=target, name=f"radar-ws-{exchange}", daemon=True)
                self._threads.append(thread)
                thread.start()

    def stop(self) -> None:
        """Request shutdown, close active sockets, and retain any unjoined workers."""
        # Serialize stop requests and prevent start() from clearing the stop
        # event while this shutdown is still joining the previous workers.
        with self._stop_lock:
            with self._lifecycle_lock:
                self._stopping = True
                self._stop.set()
                apps = list(self._apps.values())
                threads = list(self._threads)
            # Closing before run_forever() begins can be too early for
            # websocket-client: run_forever may reset its internal running flag.
            # Retry close while joining so a startup/close race gets another
            # close after the socket loop has actually entered.
            deadline = time.monotonic() + 3.0
            while True:
                for app in apps:
                    try:
                        app.close()
                    except Exception:
                        pass
                alive = [thread for thread in threads if thread.is_alive()]
                if not alive:
                    break
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                for thread in alive:
                    thread.join(timeout=min(0.05, remaining))
            with self._lifecycle_lock:
                self._threads = [thread for thread in self._threads if thread.is_alive()]
                with self._lock:
                    state = "stopping" if self._threads else "stopped"
                    for exchange in self.exchanges:
                        self._connection_state[exchange] = state
                self._stopping = False

    def _emit(self, event: MarketEvent) -> None:
        key = (event.exchange, event.symbol)
        with self._lock:
            if event.trade_id is not None:
                identity = (event.exchange, event.symbol, str(event.trade_id))
                if identity in self._seen_trade_ids:
                    return
                self._seen_trade_ids[identity] = None
                while len(self._seen_trade_ids) > self._max_seen_trade_ids:
                    self._seen_trade_ids.popitem(last=False)
            previous_moves = list(self._last_move.items())
            self._last_price[key] = event.price
            self._events_total += 1
            self._events_by_exchange[event.exchange] = self._events_by_exchange.get(event.exchange, 0) + 1
            self._last_event[event.exchange] = {
                "symbol": event.symbol,
                "price": event.price,
                "exchange_ts_ms": event.exchange_ts_ms,
                "local_ts_ms": event.local_ts_ms,
            }
            if event.price_before is not None:
                move = (event.price - event.price_before) / event.price_before if event.price_before else 0.0
                if abs(move) >= self.min_move:
                    self._last_move[key] = event

        self._remember_market_event(event)
        self._match_candidate(event, previous_moves)
        if self.callback:
            try:
                self.callback(event)
            except Exception:
                # A consumer must never kill the public market-data loop.
                pass
        self._persist(event)

    
    def _remember_market_event(self, event: MarketEvent) -> None:
        with self._lock:
            rows = self._recent_market_events.setdefault(event.symbol, [])
            rows.append(event)
            if len(rows) > 256:
                del rows[:-256]

    def ingest_external_observation(
        self,
        observation: ExternalMarketObservation,
    ) -> SourceLatencyObservation | None:
        """Ingest one normalized external observation into the PAPER profiler."""
        validate_observation(observation)
        return self.record_external_source(
            source_id=observation.source_id,
            symbol=observation.symbol,
            source_ts_ms=observation.source_ts_ms,
            source_price=observation.price,
            direction=observation.direction,
            observed_ts_ms=observation.received_ts_ms,
        )

    def record_external_source(
        self,
        *,
        source_id: str,
        symbol: str,
        source_ts_ms: int,
        source_price: float,
        direction: str | None = None,
        observed_ts_ms: int | None = None,
    ) -> SourceLatencyObservation | None:
        """Ingest one timestamped external observation for PAPER research.

        Adapters should call this only for official/compliant external feeds.
        The profiler matches the observation against the first reference-market
        event that occurs after the source timestamp.
        """
        profiler = self.external_latency_profiler
        if profiler is None:
            return None
        normalized = str(symbol).upper().replace("-", "/")
        with self._lock:
            candidates = [
                event for event in self._recent_market_events.get(normalized, [])
                if event.exchange_ts_ms >= int(source_ts_ms)
            ]
        if not candidates:
            return None
        reference = min(candidates, key=lambda event: event.exchange_ts_ms)
        return profiler.record(
            source_id=source_id,
            symbol=normalized,
            source_ts_ms=int(source_ts_ms),
            source_price=float(source_price),
            market_ts_ms=reference.exchange_ts_ms,
            market_price=reference.price,
            direction=direction,
            observed_ts_ms=observed_ts_ms,
        )

    def _match_candidate(self, event: MarketEvent, previous_moves: list[tuple[tuple[str, str], MarketEvent]]) -> None:
        if event.price_before is None or event.price_before <= 0:
            return
        follower_move = (event.price - event.price_before) / event.price_before
        if abs(follower_move) < self.min_move:
            return
        for (exchange, symbol), leader in previous_moves:
            if symbol != event.symbol or exchange == event.exchange or leader.price_before is None or leader.price_before <= 0:
                continue
            lag = event.exchange_ts_ms - leader.exchange_ts_ms
            receive_lag = event.local_ts_ms - leader.local_ts_ms
            # Exchange timestamps alone do not prove that the leader was
            # observable first. Reject causally inverted or locally stale
            # candidates before they reach PAPER edge statistics.
            if lag < 0 or lag > self.lead_window_ms:
                continue
            if receive_lag < 0 or receive_lag > self.lead_window_ms:
                continue
            leader_move = (leader.price - leader.price_before) / leader.price_before
            if abs(leader_move) < self.min_move or leader_move * follower_move <= 0:
                continue
            lead = LeadLagEvent(
                symbol=event.symbol,
                leader=leader.exchange,
                follower=event.exchange,
                direction="UP" if leader_move > 0 else "DOWN",
                leader_exchange_ts_ms=leader.exchange_ts_ms,
                follower_exchange_ts_ms=event.exchange_ts_ms,
                exchange_lag_ms=lag,
                leader_receive_ts_ms=leader.local_ts_ms,
                follower_receive_ts_ms=event.local_ts_ms,
                receive_lag_ms=receive_lag,
                leader_move_bps=round(leader_move * 10000, 3),
                follower_move_bps=round(follower_move * 10000, 3),
            )
            self._persist_lead_lag(lead)
            edge = self.latency_detector.observe_event(lead)
            self._persist_latency_edge(edge)

    def _append_jsonl(self, path: Path, row: object) -> None:
        """Append one JSONL record and expose failures without stopping collection."""
        try:
            serialized = json.dumps(asdict(row), ensure_ascii=False, allow_nan=False)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(serialized + "\n")
        except Exception:
            # Disk/serialization faults must be visible in health snapshots but
            # must not terminate the public feed or its callback path.
            with self._lock:
                self._persistence_errors += 1

    def _persist(self, event: MarketEvent) -> None:
        self._append_jsonl(self.data_dir / "websocket_events.jsonl", event)

    def _persist_lead_lag(self, lead: LeadLagEvent) -> None:
        self._append_jsonl(self.data_dir / "websocket_lead_lag.jsonl", lead)

    def _persist_latency_edge(self, edge: object) -> None:
        self._append_jsonl(self.data_dir / "websocket_latency_edges.jsonl", edge)

    def _run_binance(self) -> None:
        streams = "/".join(f"{self.normalize_symbol(s)[0].lower()}{self.normalize_symbol(s)[1].lower()}@trade" for s in self.symbols)
        self._run_with_reconnect(self.ENDPOINTS["binance"].format(streams=streams), self._parse_binance, "binance")

    def _run_coinbase(self) -> None:
        def on_open(ws: websocket.WebSocketApp) -> None:
            products = [f"{self.normalize_symbol(s)[0]}-{self.normalize_symbol(s)[1]}" for s in self.symbols]
            ws.send(json.dumps({"type": "subscribe", "product_ids": products, "channel": "market_trades"}))
        self._run_with_reconnect(self.ENDPOINTS["coinbase"], self._parse_coinbase, "coinbase", on_open)

    def _run_okx(self) -> None:
        def on_open(ws: websocket.WebSocketApp) -> None:
            args = [{"channel": "trades", "instId": s.replace("/", "-").upper()} for s in self.symbols]
            ws.send(json.dumps({"op": "subscribe", "args": args}))
        self._run_with_reconnect(self.ENDPOINTS["okx"], self._parse_okx, "okx", on_open)

    @staticmethod
    def _next_reconnect_delay(current_delay: float, connection_seconds: float,
                              stable_connection_seconds: float = 60.0,
                              max_delay_seconds: float = 30.0) -> float:
        """Bound retry growth; reset only after a connection stayed up long enough."""
        if connection_seconds >= stable_connection_seconds:
            return 1.0
        return min(max(1.0, float(current_delay)) * 2.0, max_delay_seconds)

    def _run_with_reconnect(self, url: str, parser: Callable[[dict, int], list[MarketEvent]],
                            exchange: str, on_open: Callable[[websocket.WebSocketApp], None] | None = None) -> None:
        delay = 1.0
        while not self._stop.is_set():
            def handle_message(_ws: websocket.WebSocketApp, raw: str) -> None:
                receive_ts = self._now_ms()
                with self._lock:
                    self._last_message_ts_ms[exchange] = receive_ts
                try:
                    for event in parser(json.loads(raw), receive_ts):
                        self._emit(event)
                except Exception:
                    return

            connected_at: float | None = None

            def handle_open(ws: websocket.WebSocketApp) -> None:
                nonlocal connected_at
                if on_open is not None:
                    on_open(ws)
                connected_at = time.monotonic()
                with self._lock:
                    self._connection_state[exchange] = "connected"
                    self._last_connected_ts_ms[exchange] = self._now_ms()
                    self._last_connection_error.pop(exchange, None)

            app: websocket.WebSocketApp | None = None
            with self._lock:
                self._connection_state[exchange] = "connecting"
            try:
                app = websocket.WebSocketApp(url, on_open=handle_open, on_message=handle_message)
                with self._lifecycle_lock:
                    self._apps[exchange] = app
                if self._stop.is_set():
                    app.close()
                else:
                    app.run_forever(ping_interval=20, ping_timeout=10)
            except Exception as exc:
                with self._lock:
                    self._errors[exchange] = self._errors.get(exchange, 0) + 1
                    self._last_connection_error[exchange] = type(exc).__name__
            finally:
                with self._lock:
                    # A failed connection attempt is not a disconnection event.
                    # Record disconnect time only if this attempt reached open.
                    if connected_at is not None:
                        self._last_disconnected_ts_ms[exchange] = self._now_ms()
                    self._connection_state[exchange] = "stopped" if self._stop.is_set() else "reconnecting"
                if app is not None:
                    with self._lifecycle_lock:
                        if self._apps.get(exchange) is app:
                            self._apps.pop(exchange, None)
                # Only time spent after the socket opened counts as stable uptime;
                # DNS/connect stalls must not reset the backoff.
                elapsed = 0.0 if connected_at is None else max(0.0, time.monotonic() - connected_at)

            if self._stop.is_set():
                break

            # A normal return can also mean an unexpected disconnect. Apply
            # backoff to both normal closes and exceptions to prevent tight loops.
            delay = self._next_reconnect_delay(delay, elapsed)
            with self._lock:
                self._reconnects[exchange] = self._reconnects.get(exchange, 0) + 1
            wait_seconds = delay * random.uniform(0.8, 1.2)
            self._stop.wait(wait_seconds)

    def _make_event(self, exchange: str, symbol: str, price: float, quantity: float,
                    side: str, exchange_ts: int, receive_ts: int,
                    trade_id: object = None) -> MarketEvent:
        previous = self._last_price.get((exchange, symbol))
        # Venue event time and collector wall time have different clock domains.
        # Their difference is not one-way network latency without clock calibration.
        normalized_trade_id = None if trade_id is None else (str(trade_id).strip() or None)
        return MarketEvent(exchange, symbol, price, quantity, side, exchange_ts,
                           receive_ts, None, previous, normalized_trade_id)

    @staticmethod
    def _parse_finite_number(value: object) -> float | None:
        """Reject malformed, non-finite, negative, or zero market values.

        Both prices and trade quantities must be strictly positive. Invalid
        venue payloads must not contaminate move detection.
        """
        if value is None or isinstance(value, bool):
            return None
        try:
            number = float(value)
        except (TypeError, ValueError, OverflowError):
            return None
        if not math.isfinite(number):
            return None
        if number <= 0:
            return None
        return number

    @staticmethod
    def _parse_trade_side(value: object) -> str | None:
        """Normalize only explicit venue BUY/SELL sides; unknown sides are unsafe."""
        if not isinstance(value, str):
            return None
        side = value.strip().upper()
        return side if side in {"BUY", "SELL"} else None

    @staticmethod
    def _parse_positive_timestamp_ms(value: object) -> int | None:
        """Return a valid positive venue timestamp; never substitute local receive time."""
        if value is None or isinstance(value, bool):
            return None
        try:
            timestamp = int(value)
        except (TypeError, ValueError, OverflowError):
            return None
        return timestamp if timestamp > 0 else None

    def _parse_binance(self, payload: dict, receive_ts: int) -> list[MarketEvent]:
        data = payload.get("data", payload)
        if data.get("e") != "trade" or not isinstance(data.get("m"), bool):
            return []
        symbol = self._to_symbol(data.get("s", ""))
        timestamp = self._parse_positive_timestamp_ms(data.get("T"))
        if not symbol or timestamp is None:
            return []
        price = self._parse_finite_number(data.get("p"))
        quantity = self._parse_finite_number(data.get("q"))
        if price is None or quantity is None:
            return []
        side = "SELL" if data["m"] else "BUY"
        return [self._make_event("binance", symbol, price, quantity, side, timestamp, receive_ts, data.get("t"))]

    def _parse_coinbase(self, payload: dict, receive_ts: int) -> list[MarketEvent]:
        if payload.get("channel") != "market_trades":
            return []
        events: list[MarketEvent] = []
        for item in payload.get("events", []):
            for trade in item.get("trades", []):
                symbol = self._to_symbol(trade.get("product_id", "").replace("-", "/"))
                if symbol:
                    timestamp = self._parse_iso_ms(trade.get("time"))
                    if timestamp is None:
                        continue
                    price = self._parse_finite_number(trade.get("price"))
                    quantity = self._parse_finite_number(trade.get("size"))
                    side = self._parse_trade_side(trade.get("side"))
                    if price is None or quantity is None or side is None:
                        continue
                    events.append(self._make_event("coinbase", symbol, price, quantity, side, timestamp, receive_ts, trade.get("trade_id")))
        return events

    def _parse_okx(self, payload: dict, receive_ts: int) -> list[MarketEvent]:
        if payload.get("arg", {}).get("channel") != "trades":
            return []
        events: list[MarketEvent] = []
        for trade in payload.get("data", []):
            symbol = self._to_symbol(str(trade.get("instId", "")).replace("-", "/"))
            if symbol:
                timestamp = self._parse_positive_timestamp_ms(trade.get("ts"))
                if timestamp is None:
                    continue
                price = self._parse_finite_number(trade.get("px"))
                quantity = self._parse_finite_number(trade.get("sz"))
                side = self._parse_trade_side(trade.get("side"))
                if price is None or quantity is None or side is None:
                    continue
                events.append(self._make_event("okx", symbol, price, quantity, side, timestamp, receive_ts, trade.get("tradeId")))
        return events

    def _to_symbol(self, symbol: str) -> str | None:
        normalized = symbol.upper().replace("-", "/")
        wanted = {s.upper() for s in self.symbols}
        if normalized in wanted:
            return normalized
        compact = normalized.replace("/", "")
        for configured in wanted:
            if compact == configured.replace("/", ""):
                return configured
        return None

    @staticmethod
    def _parse_iso_ms(value: str | None) -> int | None:
        """Parse a venue-provided ISO timestamp; missing or malformed stays unknown."""
        if not value:
            return None
        try:
            from datetime import datetime
            timestamp = int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp() * 1000)
        except (ValueError, TypeError, OverflowError):
            return None
        return timestamp if timestamp > 0 else None
