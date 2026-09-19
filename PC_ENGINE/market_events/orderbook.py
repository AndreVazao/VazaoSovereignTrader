from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class OrderBookLevel:
    price: float
    quantity: float

    def as_dict(self) -> dict[str, float]:
        return asdict(self)


@dataclass(frozen=True)
class OrderBookEvent:
    """Normalized public L2 snapshot/update event."""
    event_id: str
    venue: str
    symbol: str
    event_type: str
    sequence: int | None
    provider_ts_ms: int | None
    exchange_ts_ms: int | None
    local_receive_ns: int
    local_receive_wall_ns: int
    bids: tuple[OrderBookLevel, ...]
    asks: tuple[OrderBookLevel, ...]
    raw_source: str

    def as_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "bids": [level.as_dict() for level in self.bids],
            "asks": [level.as_dict() for level in self.asks],
        }

    @property
    def best_bid(self) -> float | None:
        return self.bids[0].price if self.bids else None

    @property
    def best_ask(self) -> float | None:
        return self.asks[0].price if self.asks else None
