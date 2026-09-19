from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from PC_ENGINE.market_events.orderbook import OrderBookEvent
from PC_ENGINE.market_events.orderbook_builder import OrderBookBuilder
from PC_ENGINE.paper.microstructure import BookLevel, OrderBookSnapshot, OrderBookSimulator


@dataclass(frozen=True)
class L2MicrostructureSample:
    event_id: str
    venue: str
    symbol: str
    sequence: int | None
    timestamp_ms: float
    spread_bps: float | None
    mid_price: float | None
    buy_requested_qty: float
    buy_filled_qty: float
    buy_vwap: float | None
    buy_consumed_levels: int
    buy_liquidity_limited: bool
    sell_requested_qty: float
    sell_filled_qty: float
    sell_vwap: float | None
    sell_consumed_levels: int
    sell_liquidity_limited: bool


@dataclass(frozen=True)
class L2MicrostructureReport:
    status: str
    events_loaded: int
    executable_books: int
    stale_events: int
    samples: int
    buy_full_fills: int
    buy_partials: int
    sell_full_fills: int
    sell_partials: int
    average_spread_bps: float | None
    average_buy_impact_bps: float | None
    average_sell_impact_bps: float | None
    started_at: float
    finished_at: float
    notes: list[str]


class L2MicrostructureReplay:
    """Turn reconstructed L2 books into executable PAPER microstructure samples.

    This layer deliberately does not generate live orders or claim strategy alpha.
    It measures what quantity could actually be executed through observed depth.
    """

    def __init__(
        self,
        input_path: str = "PC_ENGINE/data/radar/websocket_orderbook_events.jsonl",
        output_path: str = "PC_ENGINE/data/replay/l2_microstructure.json",
        notional_per_side: float = 100.0,
    ) -> None:
        self.input_path = input_path
        self.output_path = output_path
        self.notional_per_side = notional_per_side
        self.simulator = OrderBookSimulator(seed=17)

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
        events: list[OrderBookEvent] = []
        for line in source.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
                events.append(OrderBookEvent(
                    event_id=raw["event_id"],
                    venue=raw["venue"],
                    symbol=raw["symbol"],
                    event_type=raw["event_type"],
                    sequence=raw.get("sequence"),
                    sequence_start=raw.get("sequence_start"),
                    provider_ts_ms=raw.get("provider_ts_ms"),
                    exchange_ts_ms=raw.get("exchange_ts_ms"),
                    local_receive_ns=raw["local_receive_ns"],
                    local_receive_wall_ns=raw["local_receive_wall_ns"],
                    bids=tuple(BookLevel(float(x["price"]), float(x["quantity"])) for x in raw.get("bids", [])),
                    asks=tuple(BookLevel(float(x["price"]), float(x["quantity"])) for x in raw.get("asks", [])),
                    raw_source=raw.get("raw_source", "jsonl"),
                ))
            except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                continue
        events.sort(key=lambda event: (L2MicrostructureReplay._time(event), event.local_receive_ns))
        return events

    @staticmethod
    def _book(builder: OrderBookBuilder, event: OrderBookEvent) -> OrderBookSnapshot | None:
        rebuilt = builder.apply(event)
        if rebuilt is None:
            return None
        return OrderBookSnapshot(
            event.venue,
            event.symbol,
            L2MicrostructureReplay._time(event),
            tuple(BookLevel(level.price, level.quantity) for level in rebuilt.bids),
            tuple(BookLevel(level.price, level.quantity) for level in rebuilt.asks),
        )

    def run(self) -> L2MicrostructureReport:
        started = time.time()
        events = self._load(self.input_path)
        builders: dict[tuple[str, str], OrderBookBuilder] = {}
        samples: list[L2MicrostructureSample] = []
        stale_events = 0

        for event in events:
            key = (event.venue, event.symbol)
            builder = builders.setdefault(key, OrderBookBuilder(*key))
            book = self._book(builder, event)
            if book is None:
                if builder.stale:
                    stale_events += 1
                continue
            if book.best_bid is None or book.best_ask is None:
                continue

            mid = (book.best_bid + book.best_ask) / 2.0
            buy_qty = self.notional_per_side / book.best_ask
            sell_qty = self.notional_per_side / book.best_bid
            buy = self.simulator.simulate_market_order(book, side="BUY", quantity=buy_qty)
            sell = self.simulator.simulate_market_order(book, side="SELL", quantity=sell_qty)

            buy_impact = None if buy.average_price is None else (buy.average_price / mid - 1.0) * 10_000.0
            sell_impact = None if sell.average_price is None else (1.0 - sell.average_price / mid) * 10_000.0
            samples.append(L2MicrostructureSample(
                event.event_id, event.venue, event.symbol, event.sequence,
                self._time(event), book.spread_bps, mid,
                buy_qty, buy.filled_qty, buy.average_price, buy.consumed_levels, buy.liquidity_limited,
                sell_qty, sell.filled_qty, sell.average_price, sell.consumed_levels, sell.liquidity_limited,
            ))

        def avg(values: list[float]) -> float | None:
            return sum(values) / len(values) if values else None

        report = L2MicrostructureReport(
            status="EMPTY" if not events else "PAPER_L2_MICROSTRUCTURE",
            events_loaded=len(events),
            executable_books=len(samples),
            stale_events=stale_events,
            samples=len(samples),
            buy_full_fills=sum(s.buy_filled_qty >= s.buy_requested_qty for s in samples),
            buy_partials=sum(0 < s.buy_filled_qty < s.buy_requested_qty for s in samples),
            sell_full_fills=sum(s.sell_filled_qty >= s.sell_requested_qty for s in samples),
            sell_partials=sum(0 < s.sell_filled_qty < s.sell_requested_qty for s in samples),
            average_spread_bps=avg([s.spread_bps for s in samples if s.spread_bps is not None]),
            average_buy_impact_bps=avg([s for s in [x.buy_vwap for x in samples] if s is not None]),
            average_sell_impact_bps=avg([s for s in [x.sell_vwap for x in samples] if s is not None]),
            started_at=started,
            finished_at=time.time(),
            notes=[
                "PAPER only; no private credentials or live orders.",
                "Samples use reconstructed public L2 depth.",
                "Impact metrics are execution-price versus mid-price measurements, not expected profit.",
            ],
        )
        target = Path(self.output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps({
            "report": asdict(report),
            "samples": [asdict(sample) for sample in samples],
        }, indent=2), encoding="utf-8")
        return report
