from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

from PC_ENGINE.radar.depth_edge import SynchronizedBookView


@dataclass(frozen=True)
class CanonicalInstrumentMapping:
    """Explicit venue-symbol to canonical instrument mapping.

    Mapping must be sourced from validated market metadata by the caller.
    This class does not infer that two venue symbols represent equivalent
    contracts, quote assets, settlement assets, or spot/perpetual products.
    """

    venue: str
    symbol: str
    instrument_id: str
    price_unit: str

    def __post_init__(self) -> None:
        if not all(isinstance(value, str) and value.strip() for value in (self.venue, self.symbol, self.instrument_id, self.price_unit)):
            raise ValueError("mapping_fields_must_be_non_empty")


def to_synchronized_book_view(
    mapping: CanonicalInstrumentMapping,
    book: Any,
    *,
    now_ns: int,
    max_age_ms: float = 250.0,
    max_levels_per_side: int = 5000,
) -> SynchronizedBookView:
    """Adapt a venue synchronizer view for PAPER edge assessment, fail-closed.

    The adapter validates every supplied level before exposing even the
    best bid/ask. It does not infer instrument equivalence, repair sequence
    gaps, or authorize execution. now_ns and observation_time_ns must share
    the same monotonic clock domain.
    """
    if not isinstance(now_ns, int) or isinstance(now_ns, bool) or now_ns <= 0:
        raise ValueError("invalid_monotonic_now")
    try:
        max_age = float(max_age_ms)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("max_age_ms_must_be_finite_and_positive") from exc
    if not math.isfinite(max_age) or max_age <= 0:
        raise ValueError("max_age_ms_must_be_finite_and_positive")
    if (
        not isinstance(max_levels_per_side, int)
        or isinstance(max_levels_per_side, bool)
        or max_levels_per_side < 1
    ):
        raise ValueError("max_levels_per_side_must_be_positive_integer")

    raw_venue = getattr(book, "venue", mapping.venue)
    raw_symbol = getattr(book, "symbol", mapping.symbol)
    if raw_venue != mapping.venue or raw_symbol != mapping.symbol:
        return _invalid(mapping)

    raw_status = getattr(book, "status", None)
    status = getattr(raw_status, "value", raw_status)
    raw_eligible = getattr(book, "eligible", False) is True
    observation_ns = getattr(book, "observation_time_ns", None)
    sequence = getattr(book, "sequence", None)
    if sequence is None:
        sequence = getattr(book, "update_id", None)
    if (
        status != "SYNCED"
        or not raw_eligible
        or not isinstance(sequence, int)
        or isinstance(sequence, bool)
        or sequence < 0
        or not isinstance(observation_ns, int)
        or isinstance(observation_ns, bool)
        or observation_ns <= 0
        or observation_ns > now_ns
    ):
        return _invalid(mapping)

    age_ms = (now_ns - observation_ns) / 1_000_000.0
    if not math.isfinite(age_ms) or age_ms > max_age:
        return SynchronizedBookView(
            venue=mapping.venue,
            instrument_id=mapping.instrument_id,
            status="SYNCED",
            eligible=False,
            age_ms=age_ms if math.isfinite(age_ms) else None,
            best_bid=None,
            best_ask=None,
            observation_time_ns=observation_ns,
            sequence=sequence,
            price_unit=mapping.price_unit,
        )

    bids = getattr(book, "bids", ())
    asks = getattr(book, "asks", ())
    if (
        not isinstance(bids, (tuple, list))
        or not isinstance(asks, (tuple, list))
        or not bids
        or not asks
        or len(bids) > max_levels_per_side
        or len(asks) > max_levels_per_side
    ):
        return _invalid(mapping, age_ms=age_ms, observation_ns=observation_ns)

    def validated_prices(levels, *, descending: bool) -> list[float] | None:
        values: list[float] = []
        for level in levels:
            try:
                price = float(level.price)
                quantity = float(level.quantity)
            except (AttributeError, TypeError, ValueError, OverflowError):
                return None
            if (
                not math.isfinite(price)
                or price <= 0
                or not math.isfinite(quantity)
                or quantity <= 0
            ):
                return None
            values.append(price)
        if len(values) != len(set(values)):
            return None
        if values != sorted(values, reverse=descending):
            return None
        return values

    bid_prices = validated_prices(bids, descending=True)
    ask_prices = validated_prices(asks, descending=False)
    if bid_prices is None or ask_prices is None:
        return _invalid(mapping, age_ms=age_ms, observation_ns=observation_ns)

    best_bid, best_ask = bid_prices[0], ask_prices[0]
    if best_bid >= best_ask:
        return _invalid(mapping, age_ms=age_ms, observation_ns=observation_ns)

    return SynchronizedBookView(
        venue=mapping.venue,
        instrument_id=mapping.instrument_id,
        status="SYNCED",
        eligible=True,
        age_ms=age_ms,
        best_bid=best_bid,
        best_ask=best_ask,
        observation_time_ns=observation_ns,
        sequence=sequence,
        price_unit=mapping.price_unit,
    )


def _invalid(
    mapping: CanonicalInstrumentMapping,
    *,
    age_ms: float | None = None,
    observation_ns: int | None = None,
) -> SynchronizedBookView:
    return SynchronizedBookView(
        venue=mapping.venue,
        instrument_id=mapping.instrument_id,
        status="INVALID",
        eligible=False,
        age_ms=age_ms,
        best_bid=None,
        best_ask=None,
        observation_time_ns=observation_ns,
        price_unit=mapping.price_unit,
    )
