from __future__ import annotations

import json
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
    local_receive_latency_ms: int
    price_before: float | None = None


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
        self._last_price: dict[tuple[str, str], float] = {}
        self._last_move: dict[tuple[str, str], MarketEvent] = {}
        self._lock = threading.RLock()

    @staticmethod
    def normalize_symbol(symbol: str) -> tuple[str, str]:
        base, quote = symbol.upper().split("/")
        return base, quote

    @staticmethod
    def _now_ms() -> int:
        return time.time_ns() // 1_000_000

    def start(self) -> None:
        self._stop.clear()
        for exchange in self.exchanges:
            target = getattr(self, f"_run_{exchange}", None)
            if target is None:
                continue
            thread = threading.Thread(target=target, name=f"radar-ws-{exchange}", daemon=True)
            self._threads.append(thread)
            thread.start()

    def stop(self) -> None:
        self._stop.set()
        for thread in list(self._threads):
            thread.join(timeout=3)
        self._threads.clear()

    def _emit(self, event: MarketEvent) -> None:
        key = (event.exchange, event.symbol)
        with self._lock:
            previous_moves = list(self._last_move.items())
            self._last_price[key] = event.price
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
            if lag < 0 or lag > self.lead_window_ms:
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

    def _persist(self, event: MarketEvent) -> None:
        path = self.data_dir / "websocket_events.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")

    def _persist_lead_lag(self, lead: LeadLagEvent) -> None:
        path = self.data_dir / "websocket_lead_lag.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(lead), ensure_ascii=False) + "\n")

    def _persist_latency_edge(self, edge: object) -> None:
        path = self.data_dir / "websocket_latency_edges.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(edge), ensure_ascii=False) + "\n")

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

    def _run_with_reconnect(self, url: str, parser: Callable[[dict, int], list[MarketEvent]],
                            exchange: str, on_open: Callable[[websocket.WebSocketApp], None] | None = None) -> None:
        delay = 1.0
        while not self._stop.is_set():
            def handle_message(_ws: websocket.WebSocketApp, raw: str) -> None:
                receive_ts = self._now_ms()
                try:
                    for event in parser(json.loads(raw), receive_ts):
                        self._emit(event)
                except Exception:
                    return
            app = websocket.WebSocketApp(url, on_open=on_open, on_message=handle_message)
            try:
                app.run_forever(ping_interval=20, ping_timeout=10)
                delay = 1.0
            except Exception:
                delay = min(delay * 2.0, 30.0)
            if not self._stop.is_set():
                self._stop.wait(delay)

    def _make_event(self, exchange: str, symbol: str, price: float, quantity: float,
                    side: str, exchange_ts: int, receive_ts: int) -> MarketEvent:
        previous = self._last_price.get((exchange, symbol))
        return MarketEvent(exchange, symbol, price, quantity, side, exchange_ts,
                           receive_ts, max(0, receive_ts - exchange_ts), previous)

    def _parse_binance(self, payload: dict, receive_ts: int) -> list[MarketEvent]:
        data = payload.get("data", payload)
        if data.get("e") != "trade":
            return []
        symbol = self._to_symbol(data.get("s", ""))
        if not symbol:
            return []
        ts = int(data.get("T") or data.get("E") or receive_ts)
        return [self._make_event("binance", symbol, float(data["p"]), float(data["q"]), "SELL" if bool(data.get("m")) else "BUY", ts, receive_ts)]

    def _parse_coinbase(self, payload: dict, receive_ts: int) -> list[MarketEvent]:
        if payload.get("channel") != "market_trades":
            return []
        events: list[MarketEvent] = []
        for item in payload.get("events", []):
            for trade in item.get("trades", []):
                symbol = self._to_symbol(trade.get("product_id", "").replace("-", "/"))
                if symbol:
                    ts = self._parse_iso_ms(trade.get("time"), receive_ts)
                    events.append(self._make_event("coinbase", symbol, float(trade["price"]), float(trade["size"]), str(trade.get("side", "")).upper(), ts, receive_ts))
        return events

    def _parse_okx(self, payload: dict, receive_ts: int) -> list[MarketEvent]:
        if payload.get("arg", {}).get("channel") != "trades":
            return []
        events: list[MarketEvent] = []
        for trade in payload.get("data", []):
            symbol = self._to_symbol(str(trade.get("instId", "")).replace("-", "/"))
            if symbol:
                ts = int(trade.get("ts") or receive_ts)
                events.append(self._make_event("okx", symbol, float(trade["px"]), float(trade["sz"]), str(trade.get("side", "")).upper(), ts, receive_ts))
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
    def _parse_iso_ms(value: str | None, fallback: int) -> int:
        if not value:
            return fallback
        try:
            from datetime import datetime
            return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp() * 1000)
        except (ValueError, TypeError):
            return fallback
