from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class MarketEvent:
    """Normalized market event with an explicit timing chain.

    Local elapsed timing uses the monotonic clock. Venue/provider timestamps
    remain epoch milliseconds. Local wall-clock receive time bridges those
    domains for calibration and is never treated as authoritative market time.
    """

    event_id: str
    venue: str
    symbol: str
    event_type: str
    sequence: int | None
    provider_ts_ms: int | None
    exchange_ts_ms: int | None
    local_receive_ns: int
    local_receive_wall_ns: int
    local_process_ns: int
    browser_render_ns: int | None
    price: float | None
    bid: float | None
    ask: float | None
    volume: float | None
    raw_source: str

    @property
    def processing_delay_ns(self) -> int:
        return max(0, self.local_process_ns - self.local_receive_ns)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class MarketEventFactory:
    """Build normalized events without inventing venue timing information."""

    @staticmethod
    def create(
        *,
        venue: str,
        symbol: str,
        event_type: str,
        provider_ts_ms: int | None = None,
        exchange_ts_ms: int | None = None,
        sequence: int | None = None,
        price: float | None = None,
        bid: float | None = None,
        ask: float | None = None,
        volume: float | None = None,
        raw_source: str = "api",
        browser_render_ns: int | None = None,
        receive_ns: int | None = None,
        receive_wall_ns: int | None = None,
        process_ns: int | None = None,
    ) -> MarketEvent:
        receive = time.monotonic_ns() if receive_ns is None else receive_ns
        receive_wall = time.time_ns() if receive_wall_ns is None else receive_wall_ns
        process = time.monotonic_ns() if process_ns is None else process_ns
        if process < receive:
            raise ValueError("process_ns cannot be earlier than receive_ns")
        return MarketEvent(
            event_id=uuid.uuid4().hex,
            venue=venue,
            symbol=symbol,
            event_type=event_type,
            sequence=sequence,
            provider_ts_ms=provider_ts_ms,
            exchange_ts_ms=exchange_ts_ms,
            local_receive_ns=receive,
            local_receive_wall_ns=receive_wall,
            local_process_ns=process,
            browser_render_ns=browser_render_ns,
            price=price,
            bid=bid,
            ask=ask,
            volume=volume,
            raw_source=raw_source,
        )
