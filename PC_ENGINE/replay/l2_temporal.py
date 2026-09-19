from __future__ import annotations

import json
import time
import uuid
from bisect import bisect_left
from dataclasses import asdict, dataclass
from pathlib import Path

from PC_ENGINE.market_events.normalized import MarketEvent
from PC_ENGINE.market_events.orderbook import OrderBookEvent, OrderBookLevel
from PC_ENGINE.market_events.orderbook_builder import OrderBookBuilder
from PC_ENGINE.paper.microstructure import BookLevel, OrderBookSnapshot, OrderBookSimulator
from PC_ENGINE.radar.realtime_lead_lag import RealtimeLeadLagEngine


@dataclass(frozen=True)
class L2TemporalConfig:
    input_path: str = "PC_ENGINE/data/radar/websocket_orderbook_events.jsonl"
    output_path: str = "PC_ENGINE/data/replay/l2_temporal_replay.json"
    capital_per_trade: float = 100.0
    fee_bps: float = 10.0
    latency_ms: float = 80.0
    holding_ms: float = 1000.0
    max_lag_ms: float = 750.0
    min_move_bps: float = 5.0
    min_confidence: float = 0.60
    max_execution_impact_bps: float = 50.0


@dataclass(frozen=True)
class L2TemporalTrade:
    trade_id: str
    signal_event_id: str
    leader: str
    follower: str
    symbol: str
    direction: str
    signal_time_ms: float
    entry_time_ms: float | None
    exit_time_ms: float | None
    requested_qty: float
    entry_filled_qty: float
    exit_filled_qty: float
    entry_vwap: float | None
    exit_vwap: float | None
    entry_impact_bps: float | None
    exit_impact_bps: float | None
    gross_pnl: float
    fees: float
    net_pnl: float
    status: str
    lag_ms: float
    confidence: float


@dataclass(frozen=True)
class L2TemporalReport:
    run_id: str
    status: str
    events_loaded: int
    reconstructed_events: int
    signals: int
    completed: int
    partials: int
    missed: int
    rejected_by_impact: int
    net_pnl: float
    gross_pnl: float
    fees: float
    max_drawdown: float
    average_entry_impact_bps: float | None
    average_exit_impact_bps: float | None
    started_at: float
    finished_at: float
    notes: list[str]


class L2TemporalExecutableReplay:
    """Replay lead/lag signals against reconstructed L2 depth in PAPER mode.

    A signal is produced only from books reconstructed up to the current event.
    Entry is delayed by configured latency, then executed against the follower's
    observed depth. Exit is executed against observed depth after holding time.
    No live exchange order is created.
    """

    def __init__(self, config: L2TemporalConfig):
        self.config = config
        self.simulator = OrderBookSimulator(seed=23)

    @staticmethod
    def _time(event: OrderBookEvent) -> float:
        if event.exchange_ts_ms is not None:
            return float(event.exchange_ts_ms)
        if event.provider_ts_ms is not None:
            return float(event.provider_ts_ms)
        return event.local_receive_wall_ns / 1_000_000.0

    @staticmethod
    def _load(path: str) -> list[OrderBookEvent]:
        source = Path(path)
        if not source.exists():
            return []
        result: list[OrderBookEvent] = []
        for line in source.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
                result.append(OrderBookEvent(
                    event_id=raw["event_id"], venue=raw["venue"], symbol=raw["symbol"],
                    event_type=raw["event_type"], sequence=raw.get("sequence"),
                    sequence_start=raw.get("sequence_start"),
                    provider_ts_ms=raw.get("provider_ts_ms"),
                    exchange_ts_ms=raw.get("exchange_ts_ms"),
                    local_receive_ns=raw["local_receive_ns"],
                    local_receive_wall_ns=raw["local_receive_wall_ns"],
                    bids=tuple(OrderBookLevel(float(x["price"]), float(x["quantity"])) for x in raw.get("bids", [])),
                    asks=tuple(OrderBookLevel(float(x["price"]), float(x["quantity"])) for x in raw.get("asks", [])),
                    raw_source=raw.get("raw_source", "jsonl"),
                ))
            except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                continue
        result.sort(key=lambda e: (L2TemporalExecutableReplay._time(e), e.local_receive_ns))
        return result

    @staticmethod
    def _snapshot(event: OrderBookEvent, rebuilt) -> OrderBookSnapshot | None:
        if rebuilt.best_bid is None or rebuilt.best_ask is None:
            return None
        return OrderBookSnapshot(
            event.venue, event.symbol, L2TemporalExecutableReplay._time(event),
            tuple(BookLevel(x.price, x.quantity) for x in rebuilt.bids),
            tuple(BookLevel(x.price, x.quantity) for x in rebuilt.asks),
        )

    @staticmethod
    def _market_event(event: OrderBookEvent, book: OrderBookSnapshot) -> MarketEvent:
        mid = (book.best_bid + book.best_ask) / 2.0
        return MarketEvent(
            event_id=event.event_id, venue=event.venue, symbol=event.symbol,
            event_type="l2_book", sequence=event.sequence,
            provider_ts_ms=event.provider_ts_ms, exchange_ts_ms=event.exchange_ts_ms,
            local_receive_ns=event.local_receive_ns,
            local_receive_wall_ns=event.local_receive_wall_ns,
            local_process_ns=event.local_receive_ns,
            browser_render_ns=None, price=mid, bid=book.best_bid, ask=book.best_ask,
            volume=None, raw_source=event.raw_source,
        )

    @staticmethod
    def _impact(fill, mid: float | None, side: str) -> float | None:
        if fill.average_price is None or mid is None or mid <= 0:
            return None
        if side == "BUY":
            return (fill.average_price / mid - 1.0) * 10_000.0
        return (1.0 - fill.average_price / mid) * 10_000.0

    @staticmethod
    def _at_or_after(series: list[tuple[float, OrderBookSnapshot]], target: float) -> tuple[float, OrderBookSnapshot] | None:
        times = [x[0] for x in series]
        idx = bisect_left(times, target)
        return series[idx] if idx < len(series) else None

    def run(self) -> L2TemporalReport:
        started = time.time()
        events = self._load(self.config.input_path)
        builders: dict[tuple[str, str], OrderBookBuilder] = {}
        books: list[tuple[float, OrderBookSnapshot, OrderBookEvent]] = []
        stale = 0

        for event in events:
            key = (event.venue, event.symbol)
            builder = builders.setdefault(key, OrderBookBuilder(*key))
            rebuilt = builder.apply(event)
            if rebuilt is None:
                if builder.stale:
                    stale += 1
                continue
            snapshot = self._snapshot(event, rebuilt)
            if snapshot is not None:
                books.append((self._time(event), snapshot, event))

        books.sort(key=lambda x: (x[0], x[2].local_receive_ns))
        by_key: dict[tuple[str, str], list[tuple[float, OrderBookSnapshot]]] = {}
        event_by_id: dict[str, OrderBookEvent] = {}
        for timestamp, book, event in books:
            by_key.setdefault((book.venue, book.symbol), []).append((timestamp, book))
            event_by_id[event.event_id] = event

        engine = RealtimeLeadLagEngine(
            max_lag_ms=self.config.max_lag_ms,
            min_move_bps=self.config.min_move_bps,
            min_confidence=self.config.min_confidence,
        )
        trades: list[L2TemporalTrade] = []

        for timestamp, book, event in books:
            signal = engine.observe(self._market_event(event, book))
            if signal is None:
                continue
            follower_series = by_key.get((signal.follower, signal.symbol), [])
            entry = self._at_or_after(follower_series, timestamp + max(0.0, self.config.latency_ms))
            if entry is None:
                trades.append(L2TemporalTrade(
                    uuid.uuid4().hex, signal.leader_event_id, signal.leader, signal.follower,
                    signal.symbol, signal.direction, timestamp, None, None, 0.0, 0.0, 0.0,
                    None, None, None, None, 0.0, 0.0, 0.0, "MISSED_ENTRY",
                    signal.lag_ms, signal.confidence))
                continue

            entry_time, entry_book = entry
            side = "BUY" if signal.direction == "UP" else "SELL"
            mid = (entry_book.best_bid + entry_book.best_ask) / 2.0
            requested_qty = self.config.capital_per_trade / (entry_book.best_ask if side == "BUY" else entry_book.best_bid)
            entry_fill = self.simulator.simulate_market_order(entry_book, side=side, quantity=requested_qty)
            entry_impact = self._impact(entry_fill, mid, side)
            if entry_fill.filled_qty <= 0 or (entry_impact is not None and entry_impact > self.config.max_execution_impact_bps):
                trades.append(L2TemporalTrade(
                    uuid.uuid4().hex, signal.leader_event_id, signal.leader, signal.follower,
                    signal.symbol, signal.direction, timestamp, entry_time, None,
                    requested_qty, entry_fill.filled_qty, 0.0, entry_fill.average_price, None,
                    entry_impact, None, 0.0, 0.0, 0.0,
                    "IMPACT_REJECTED" if entry_fill.filled_qty > 0 else "NO_LIQUIDITY",
                    signal.lag_ms, signal.confidence))
                continue

            exit = self._at_or_after(follower_series, entry_time + max(0.0, self.config.holding_ms))
            if exit is None:
                trades.append(L2TemporalTrade(
                    uuid.uuid4().hex, signal.leader_event_id, signal.leader, signal.follower,
                    signal.symbol, signal.direction, timestamp, entry_time, None,
                    requested_qty, entry_fill.filled_qty, 0.0, entry_fill.average_price, None,
                    entry_impact, None, 0.0, 0.0, 0.0, "NO_EXIT",
                    signal.lag_ms, signal.confidence))
                continue

            exit_time, exit_book = exit
            exit_side = "SELL" if side == "BUY" else "BUY"
            exit_mid = (exit_book.best_bid + exit_book.best_ask) / 2.0
            exit_fill = self.simulator.simulate_market_order(
                exit_book, side=exit_side, quantity=entry_fill.filled_qty
            )
            exit_impact = self._impact(exit_fill, exit_mid, exit_side)
            if exit_fill.filled_qty <= 0:
                status = "EXIT_NO_LIQUIDITY"
            elif exit_fill.filled_qty < entry_fill.filled_qty:
                status = "PARTIAL_EXIT"
            else:
                status = "COMPLETED"

            matched_qty = min(entry_fill.filled_qty, exit_fill.filled_qty)
            if side == "BUY":
                gross = ((exit_fill.average_price or 0.0) - (entry_fill.average_price or 0.0)) * matched_qty
            else:
                gross = ((entry_fill.average_price or 0.0) - (exit_fill.average_price or 0.0)) * matched_qty
            fees = ((entry_fill.average_price or 0.0) * matched_qty + (exit_fill.average_price or 0.0) * matched_qty) * max(0.0, self.config.fee_bps) / 10_000.0

            trades.append(L2TemporalTrade(
                uuid.uuid4().hex, signal.leader_event_id, signal.leader, signal.follower,
                signal.symbol, signal.direction, timestamp, entry_time, exit_time,
                requested_qty, entry_fill.filled_qty, exit_fill.filled_qty,
                entry_fill.average_price, exit_fill.average_price, entry_impact, exit_impact,
                gross, fees, gross - fees, status, signal.lag_ms, signal.confidence))

        completed = [t for t in trades if t.status in {"COMPLETED", "PARTIAL_EXIT"} and t.exit_filled_qty > 0]
        pnl = sum(t.net_pnl for t in completed)
        gross = sum(t.gross_pnl for t in completed)
        fees = sum(t.fees for t in completed)
        entry_impacts = [t.entry_impact_bps for t in completed if t.entry_impact_bps is not None]
        exit_impacts = [t.exit_impact_bps for t in completed if t.exit_impact_bps is not None]
        equity = peak = max_dd = 0.0
        for trade in completed:
            equity += trade.net_pnl
            peak = max(peak, equity)
            max_dd = max(max_dd, peak - equity)

        report = L2TemporalReport(
            run_id=uuid.uuid4().hex,
            status="EMPTY" if not events else "PAPER_L2_TEMPORAL_REPLAY",
            events_loaded=len(events), reconstructed_events=len(books), signals=len(trades),
            completed=len(completed), partials=sum(t.status == "PARTIAL_EXIT" for t in trades),
            missed=sum(t.status == "MISSED_ENTRY" for t in trades),
            rejected_by_impact=sum(t.status == "IMPACT_REJECTED" for t in trades),
            net_pnl=pnl, gross_pnl=gross, fees=fees, max_drawdown=max_dd,
            average_entry_impact_bps=(sum(entry_impacts) / len(entry_impacts)) if entry_impacts else None,
            average_exit_impact_bps=(sum(exit_impacts) / len(exit_impacts)) if exit_impacts else None,
            started_at=started, finished_at=time.time(),
            notes=[
                "PAPER only; no private credentials or live orders.",
                "Signals are generated from reconstructed L2 books in replay order.",
                "Entry and exit are simulated through observed follower depth.",
                "Fees are charged on matched entry/exit quantity.",
                "Impact rejection is a safety filter, not evidence of profitability.",
                f"Observed stale/unreconstructable L2 events: {stale}.",
            ],
        )
        target = Path(self.config.output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps({
            "report": asdict(report),
            "trades": [asdict(t) for t in trades],
        }, indent=2), encoding="utf-8")
        return report
