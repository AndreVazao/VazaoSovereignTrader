from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from PC_ENGINE.market_events.normalized import MarketEvent
from PC_ENGINE.paper.microstructure import BookLevel, OrderBookSnapshot, OrderBookSimulator
from PC_ENGINE.radar.realtime_lead_lag import LeadLagSignal, RealtimeLeadLagEngine


@dataclass(frozen=True)
class MicrostructureReplayConfig:
    input_path: str = "PC_ENGINE/data/radar/websocket_events.jsonl"
    output_path: str = "PC_ENGINE/data/replay/microstructure_replay.json"
    capital_per_trade: float = 100.0
    fee_bps: float = 10.0
    slippage_bps: float = 0.0
    latency_ms: float = 80.0
    holding_ms: float = 1000.0
    min_move_bps: float = 5.0
    max_lag_ms: float = 750.0
    min_confidence: float = 0.60
    rejection_probability: float = 0.0


@dataclass(frozen=True)
class MicrostructureTrade:
    trade_id: str
    symbol: str
    venue: str
    direction: str
    signal_event_id: str
    entry_event_id: str | None
    exit_event_id: str | None
    status: str
    requested_qty: float
    filled_qty: float
    entry_price: float | None
    exit_price: float | None
    gross_pnl: float
    fees: float
    net_pnl: float
    consumed_levels: int
    liquidity_limited: bool
    rejection_reason: str | None


@dataclass
class MicrostructureReport:
    run_id: str
    status: str
    events_loaded: int
    signals: int
    trades: int
    completed: int
    partials: int
    rejections: int
    no_liquidity: int
    net_pnl: float
    gross_pnl: float
    fees: float
    max_drawdown: float
    capture_rate: float
    started_at: float
    finished_at: float
    notes: list[str]


class MicrostructureReplay:
    """PAPER replay using depth snapshots when available and conservative fallback otherwise."""

    def __init__(self, config: MicrostructureReplayConfig):
        self.config = config
        self.simulator = OrderBookSimulator(
            rejection_probability=config.rejection_probability,
            seed=7,
        )

    @staticmethod
    def _time(event: MarketEvent) -> float:
        if event.exchange_ts_ms is not None:
            return float(event.exchange_ts_ms)
        if event.provider_ts_ms is not None:
            return float(event.provider_ts_ms)
        return event.local_receive_wall_ns / 1_000_000.0

    @staticmethod
    def _price(event: MarketEvent) -> float | None:
        if event.price is not None and event.price > 0:
            return float(event.price)
        if event.bid is not None and event.ask is not None:
            return (event.bid + event.ask) / 2.0
        return None

    @staticmethod
    def _book(event: MarketEvent) -> OrderBookSnapshot:
        bid = event.bid
        ask = event.ask
        # Current normalized events do not yet carry depth arrays. Use one-level
        # executable liquidity only when a bid/ask is present; this is deliberately conservative.
        bids = (BookLevel(bid, event.volume or 0.0),) if bid and event.volume else ()
        asks = (BookLevel(ask, event.volume or 0.0),) if ask and event.volume else ()
        return OrderBookSnapshot(event.venue, event.symbol, MicrostructureReplay._time(event), bids, asks)

    @classmethod
    def _events(cls, path: str) -> list[MarketEvent]:
        source = Path(path)
        if not source.exists():
            return []
        result: list[MarketEvent] = []
        for line in source.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                result.append(MarketEvent(**json.loads(line)))
            except (TypeError, ValueError, KeyError, json.JSONDecodeError):
                continue
        result.sort(key=lambda e: (cls._time(e), e.local_receive_ns))
        return result

    @staticmethod
    def _drawdown(values: list[float]) -> float:
        equity = peak = max_dd = 0.0
        for value in values:
            equity += value
            peak = max(peak, equity)
            max_dd = max(max_dd, peak - equity)
        return max_dd

    def run(self) -> MicrostructureReport:
        started = time.time()
        events = self._events(self.config.input_path)
        engine = RealtimeLeadLagEngine(
            max_lag_ms=self.config.max_lag_ms,
            min_move_bps=self.config.min_move_bps,
            min_confidence=self.config.min_confidence,
        )
        by_key: dict[tuple[str, str], list[MarketEvent]] = {}
        for event in events:
            by_key.setdefault((event.venue, event.symbol), []).append(event)

        trades: list[MicrostructureTrade] = []
        for event in events:
            signal = engine.observe(event)
            if signal is None:
                continue
            series = by_key[(event.venue, event.symbol)]
            target = self._time(event) + self.config.latency_ms
            entry = next((item for item in series if self._time(item) >= target), None)
            if entry is None:
                trades.append(self._missed(event, signal, "latency_no_entry"))
                continue
            book = self._book(entry)
            price = self._price(entry)
            if price is None:
                trades.append(self._missed(event, signal, "no_price"))
                continue
            qty = self.config.capital_per_trade / price
            side = "BUY" if signal.direction == "UP" else "SELL"
            fill = self.simulator.simulate_market_order(book, side=side, quantity=qty)
            if fill.filled_qty <= 0:
                trades.append(self._missed(event, signal, fill.reason))
                continue

            exit_target = self._time(entry) + self.config.holding_ms
            exit_event = next((item for item in series if self._time(item) >= exit_target), None)
            if exit_event is None:
                trades.append(MicrostructureTrade(
                    uuid.uuid4().hex, event.symbol, event.venue, signal.direction,
                    signal.leader_event_id, entry.event_id, None, "NO_EXIT",
                    qty, fill.filled_qty, fill.average_price, None, 0.0, 0.0, 0.0,
                    fill.consumed_levels, fill.liquidity_limited, fill.reason,
                ))
                continue

            exit_price = self._price(exit_event)
            if exit_price is None:
                continue
            gross = ((exit_price - fill.average_price) if side == "BUY"
                     else (fill.average_price - exit_price)) * fill.filled_qty
            fees = (fill.notional + exit_price * fill.filled_qty) * self.config.fee_bps / 10_000.0
            trades.append(MicrostructureTrade(
                uuid.uuid4().hex, event.symbol, event.venue, signal.direction,
                signal.leader_event_id, entry.event_id, exit_event.event_id,
                "PARTIAL" if fill.status == "PARTIAL" else "COMPLETED",
                qty, fill.filled_qty, fill.average_price, exit_price,
                gross, fees, gross - fees, fill.consumed_levels,
                fill.liquidity_limited, fill.reason if fill.status != "FILLED" else None,
            ))

        completed = [item for item in trades if item.status in {"COMPLETED", "PARTIAL"}]
        pnl = [item.net_pnl for item in completed]
        report = MicrostructureReport(
            run_id=uuid.uuid4().hex,
            status="EMPTY" if not events else "PAPER_MICROSTRUCTURE_REPLAY",
            events_loaded=len(events),
            signals=len(trades),
            trades=len(trades),
            completed=sum(item.status == "COMPLETED" for item in trades),
            partials=sum(item.status == "PARTIAL" for item in trades),
            rejections=sum(item.rejection_reason == "simulated_rejection" for item in trades),
            no_liquidity=sum(item.rejection_reason in {"empty_book", "insufficient_depth"} for item in trades),
            net_pnl=sum(pnl),
            gross_pnl=sum(item.gross_pnl for item in completed),
            fees=sum(item.fees for item in completed),
            max_drawdown=self._drawdown(pnl),
            capture_rate=(len(completed) / len(trades)) if trades else 0.0,
            started_at=started,
            finished_at=time.time(),
            notes=[
                "PAPER only.",
                "Current normalized feed has top-of-book only; depth simulation is conservative until L2 snapshots are collected.",
                "No private credentials or live orders.",
            ],
        )
        self._persist(report, trades)
        return report

    @staticmethod
    def _missed(event: MarketEvent, signal: LeadLagSignal, reason: str) -> MicrostructureTrade:
        return MicrostructureTrade(
            uuid.uuid4().hex, event.symbol, event.venue, signal.direction,
            signal.leader_event_id, None, None, "MISSED", 0.0, 0.0,
            None, None, 0.0, 0.0, 0.0, 0, True, reason,
        )

    def _persist(self, report: MicrostructureReport, trades: list[MicrostructureTrade]) -> None:
        target = Path(self.config.output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps({
            "report": asdict(report),
            "trades": [asdict(item) for item in trades],
        }, indent=2), encoding="utf-8")
