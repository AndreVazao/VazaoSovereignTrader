from __future__ import annotations

import json
import time
import uuid
from bisect import bisect_left
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from PC_ENGINE.market_events.normalized import MarketEvent
from PC_ENGINE.radar.realtime_lead_lag import LeadLagSignal, RealtimeLeadLagEngine


@dataclass(frozen=True)
class ReplayConfig:
    input_path: str = "PC_ENGINE/data/radar/websocket_events.jsonl"
    output_path: str = "PC_ENGINE/data/replay/temporal_replay.json"
    capital_per_trade: float = 100.0
    fee_bps: float = 10.0
    slippage_bps: float = 2.0
    latency_ms: float = 80.0
    holding_ms: float = 1000.0
    max_lag_ms: float = 750.0
    min_move_bps: float = 5.0
    min_confidence: float = 0.60
    baseline_enabled: bool = True
    baseline_min_move_bps: float = 5.0


@dataclass(frozen=True)
class ReplayTrade:
    trade_id: str
    strategy: str
    symbol: str
    venue: str
    direction: str
    signal_event_id: str
    entry_event_id: str | None
    exit_event_id: str | None
    signal_time_ms: float
    entry_time_ms: float | None
    exit_time_ms: float | None
    entry_price: float | None
    exit_price: float | None
    gross_pnl: float
    fees: float
    net_pnl: float
    status: str
    signal_lag_ms: float | None
    signal_confidence: float | None


@dataclass
class ReplayReport:
    run_id: str
    status: str
    input_path: str
    events_loaded: int
    events_replayed: int
    signals: int
    strategy_trades: int
    strategy_completed: int
    baseline_trades: int
    baseline_completed: int
    strategy_net_pnl: float
    baseline_net_pnl: float
    strategy_max_drawdown: float
    baseline_max_drawdown: float
    opportunity_capture_rate: float
    missed_opportunities: int
    latency_decay_ms: float
    started_at: float
    finished_at: float
    notes: list[str]


class TemporalWebSocketReplay:
    """Deterministic PAPER replay with no live exchange execution."""

    def __init__(self, config: ReplayConfig):
        self.config = config

    @staticmethod
    def _event_time_ms(event: MarketEvent) -> float:
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
            midpoint = (event.bid + event.ask) / 2.0
            return midpoint if midpoint > 0 else None
        return None

    @classmethod
    def load_events(cls, path: str | Path) -> list[MarketEvent]:
        source = Path(path)
        if not source.exists():
            return []
        events: list[MarketEvent] = []
        for line in source.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                events.append(MarketEvent(**json.loads(line)))
            except (TypeError, ValueError, KeyError, json.JSONDecodeError):
                continue
        events.sort(key=lambda e: (cls._event_time_ms(e), e.local_receive_ns))
        return events

    @classmethod
    def _series(
        cls, events: Iterable[MarketEvent]
    ) -> dict[tuple[str, str], list[MarketEvent]]:
        result: dict[tuple[str, str], list[MarketEvent]] = {}
        for event in events:
            result.setdefault((event.venue, event.symbol), []).append(event)
        return result

    @classmethod
    def _event_at_or_after(
        cls,
        series: list[MarketEvent],
        target_ms: float,
    ) -> MarketEvent | None:
        times = [cls._event_time_ms(item) for item in series]
        index = bisect_left(times, target_ms)
        return series[index] if index < len(series) else None

    def _trade(
        self,
        *,
        strategy: str,
        signal_event: MarketEvent,
        direction: str,
        by_symbol: dict[tuple[str, str], list[MarketEvent]],
        signal: LeadLagSignal | None,
    ) -> ReplayTrade:
        signal_time = self._event_time_ms(signal_event)
        series = by_symbol.get((signal_event.venue, signal_event.symbol), [])
        entry_event = self._event_at_or_after(
            series, signal_time + max(0.0, self.config.latency_ms)
        )
        if entry_event is None:
            return ReplayTrade(
                uuid.uuid4().hex, strategy, signal_event.symbol, signal_event.venue,
                direction, signal_event.event_id, None, None, signal_time, None, None,
                None, None, 0.0, 0.0, 0.0, "MISSED_LATENCY",
                None if signal is None else signal.lag_ms,
                None if signal is None else signal.confidence,
            )

        entry_price = self._price(entry_event)
        if entry_price is None:
            return ReplayTrade(
                uuid.uuid4().hex, strategy, signal_event.symbol, signal_event.venue,
                direction, signal_event.event_id, entry_event.event_id, None,
                signal_time, self._event_time_ms(entry_event), None, None,
                0.0, 0.0, 0.0, "INVALID_ENTRY",
                None if signal is None else signal.lag_ms,
                None if signal is None else signal.confidence,
            )

        exit_event = self._event_at_or_after(
            series, self._event_time_ms(entry_event) + max(0.0, self.config.holding_ms)
        )
        if exit_event is None:
            return ReplayTrade(
                uuid.uuid4().hex, strategy, signal_event.symbol, signal_event.venue,
                direction, signal_event.event_id, entry_event.event_id, None,
                signal_time, self._event_time_ms(entry_event), None, entry_price,
                0.0, 0.0, 0.0, "NO_EXIT",
                None if signal is None else signal.lag_ms,
                None if signal is None else signal.confidence,
            )

        exit_price = self._price(exit_event)
        if exit_price is None:
            return ReplayTrade(
                uuid.uuid4().hex, strategy, signal_event.symbol, signal_event.venue,
                direction, signal_event.event_id, entry_event.event_id,
                exit_event.event_id, signal_time, self._event_time_ms(entry_event),
                self._event_time_ms(exit_event), entry_price, None, 0.0, 0.0, 0.0,
                "INVALID_EXIT",
                None if signal is None else signal.lag_ms,
                None if signal is None else signal.confidence,
            )

        slip = max(0.0, self.config.slippage_bps) / 10_000.0
        entry_fill = entry_price * (1.0 + slip if direction == "UP" else 1.0 - slip)
        exit_fill = exit_price * (1.0 - slip if direction == "UP" else 1.0 + slip)
        qty = self.config.capital_per_trade / entry_fill
        gross = ((exit_fill - entry_fill) if direction == "UP" else (entry_fill - exit_fill)) * qty
        fees = (entry_fill * qty + exit_fill * qty) * max(0.0, self.config.fee_bps) / 10_000.0

        return ReplayTrade(
            uuid.uuid4().hex, strategy, signal_event.symbol, signal_event.venue,
            direction, signal_event.event_id, entry_event.event_id,
            exit_event.event_id, signal_time, self._event_time_ms(entry_event),
            self._event_time_ms(exit_event), entry_fill, exit_fill, gross, fees,
            gross - fees, "COMPLETED",
            None if signal is None else signal.lag_ms,
            None if signal is None else signal.confidence,
        )

    @staticmethod
    def _drawdown(trades: Iterable[ReplayTrade]) -> float:
        equity = peak = max_dd = 0.0
        for trade in trades:
            if trade.status != "COMPLETED":
                continue
            equity += trade.net_pnl
            peak = max(peak, equity)
            max_dd = max(max_dd, peak - equity)
        return max_dd

    def run(self) -> ReplayReport:
        started = time.time()
        events = self.load_events(self.config.input_path)
        engine = RealtimeLeadLagEngine(
            max_lag_ms=self.config.max_lag_ms,
            min_move_bps=self.config.min_move_bps,
            min_confidence=self.config.min_confidence,
        )
        by_symbol = self._series(events)
        strategy: list[ReplayTrade] = []
        baseline: list[ReplayTrade] = []
        previous_prices: dict[tuple[str, str], float] = {}
        signals = 0
        baseline_candidates = 0

        for event in events:
            price = self._price(event)
            signal = engine.observe(event)
            if signal is not None:
                signals += 1
                strategy.append(self._trade(
                    strategy="LEAD_LAG",
                    signal_event=event,
                    direction=signal.direction,
                    by_symbol=by_symbol,
                    signal=signal,
                ))

            if self.config.baseline_enabled and price is not None:
                key = (event.venue, event.symbol)
                previous = previous_prices.get(key)
                if previous is not None:
                    move_bps = (price - previous) / previous * 10_000.0
                    if abs(move_bps) >= self.config.baseline_min_move_bps:
                        baseline_candidates += 1
                        baseline.append(self._trade(
                            strategy="BASELINE",
                            signal_event=event,
                            direction="UP" if move_bps > 0 else "DOWN",
                            by_symbol=by_symbol,
                            signal=None,
                        ))
                previous_prices[key] = price

        strategy_completed = [t for t in strategy if t.status == "COMPLETED"]
        baseline_completed = [t for t in baseline if t.status == "COMPLETED"]
        strategy_net = sum(t.net_pnl for t in strategy_completed)
        baseline_net = sum(t.net_pnl for t in baseline_completed)
        lag_values = [t.signal_lag_ms for t in strategy if t.signal_lag_ms is not None]
        latency_decay = max(0.0, self.config.latency_ms - (sum(lag_values) / len(lag_values) if lag_values else 0.0))

        report = ReplayReport(
            run_id=uuid.uuid4().hex,
            status="EMPTY" if not events else "PAPER_REPLAY",
            input_path=str(self.config.input_path),
            events_loaded=len(events),
            events_replayed=len(events),
            signals=signals,
            strategy_trades=len(strategy),
            strategy_completed=len(strategy_completed),
            baseline_trades=len(baseline),
            baseline_completed=len(baseline_completed),
            strategy_net_pnl=strategy_net,
            baseline_net_pnl=baseline_net,
            strategy_max_drawdown=self._drawdown(strategy),
            baseline_max_drawdown=self._drawdown(baseline),
            opportunity_capture_rate=signals / baseline_candidates if baseline_candidates else 0.0,
            missed_opportunities=sum(t.status != "COMPLETED" for t in strategy),
            latency_decay_ms=latency_decay,
            started_at=started,
            finished_at=time.time(),
            notes=[
                "PAPER only: no exchange orders are sent.",
                "Signal generation only sees events up to the replay cursor.",
                "Latency is simulated by delaying entry to the first follower event after the latency window.",
                "Future events are used only to score post-entry outcomes.",
                "Exchange/provider timestamps are preferred; local receive wall time is fallback.",
                "Browser-render timing is not treated as market timing.",
            ],
        )
        self._persist(report, strategy, baseline)
        return report

    def _persist(
        self,
        report: ReplayReport,
        strategy: list[ReplayTrade],
        baseline: list[ReplayTrade],
    ) -> None:
        target = Path(self.config.output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {
            "report": asdict(report),
            "strategy_trades": [asdict(item) for item in strategy],
            "baseline_trades": [asdict(item) for item in baseline],
        }
        target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
