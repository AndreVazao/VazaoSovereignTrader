from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ExternalMarketObservation:
    """Normalized timestamped observation from an external market-information source.

    Adapters are observational only. They must not expose credentials, submit orders,
    or mutate execution state.
    """

    source_id: str
    symbol: str
    price: float
    source_ts_ms: int
    direction: str | None = None
    sequence: int | None = None
    received_ts_ms: int | None = None


class ExternalSourceAdapter(Protocol):
    source_id: str

    def poll(self) -> list[ExternalMarketObservation]:
        """Return normalized observations from an official/compliant source."""
        ...


def validate_observation(observation: ExternalMarketObservation) -> None:
    source_id = str(observation.source_id).strip()
    symbol = str(observation.symbol).strip().upper()
    if not source_id:
        raise ValueError("source_id_required")
    if not symbol or "/" not in symbol:
        raise ValueError("normalized_symbol_required")
    if float(observation.price) <= 0:
        raise ValueError("price_must_be_positive")
    if int(observation.source_ts_ms) <= 0:
        raise ValueError("source_timestamp_must_be_positive")
    if observation.direction is not None:
        direction = str(observation.direction).upper()
        if direction not in {"UP", "DOWN", "FLAT"}:
            raise ValueError("invalid_direction")
    if observation.received_ts_ms is not None and int(observation.received_ts_ms) <= 0:
        raise ValueError("received_timestamp_must_be_positive")


def observation_quality(observation: ExternalMarketObservation) -> dict[str, float | bool]:
    """Return timestamp/transport quality without turning it into trading authority."""
    validate_observation(observation)
    source_ts = int(observation.source_ts_ms)
    received_ts = int(observation.received_ts_ms or source_ts)
    transport_ms = max(0, received_ts - source_ts)
    return {
        "timestamp_valid": source_ts > 0,
        "transport_latency_ms": float(transport_ms),
        "clock_order_valid": received_ts >= source_ts,
    }
