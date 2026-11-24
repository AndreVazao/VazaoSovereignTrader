from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class L2QualityAssessment:
    analysis_eligible: bool
    quality_status: str
    quality_reason: str | None
    bid_levels: int
    ask_levels: int


def assess_l2_book_view(
    view: Any,
    *,
    max_age_ms: float = 1000.0,
    max_levels_per_side: int = 5000,
) -> L2QualityAssessment:
    """Fail-closed structural quality gate for synchronized public L2 views.

    Raw records are never discarded by this function. Callers persist the
    returned eligibility metadata alongside the original book for audit.
    """
    if not math.isfinite(max_age_ms) or max_age_ms <= 0:
        raise ValueError("invalid_max_age_ms")
    if not isinstance(max_levels_per_side, int) or isinstance(max_levels_per_side, bool) or max_levels_per_side < 1:
        raise ValueError("invalid_max_levels_per_side")

    bids = getattr(view, "bids", ())
    asks = getattr(view, "asks", ())
    bid_count = len(bids) if isinstance(bids, (list, tuple)) else 0
    ask_count = len(asks) if isinstance(asks, (list, tuple)) else 0

    def reject(reason: str) -> L2QualityAssessment:
        return L2QualityAssessment(False, "FLAGGED", reason, bid_count, ask_count)

    if getattr(view, "status", None) != "SYNCED":
        return reject("book_not_synchronized")
    if getattr(view, "eligible", False) is not True:
        reason = getattr(view, "reason", None)
        return reject(reason if isinstance(reason, str) and reason else "book_not_eligible")

    sequence = getattr(view, "sequence", None)
    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 0:
        return reject("missing_or_invalid_sequence")

    observed = getattr(view, "observation_time_ns", None)
    if not isinstance(observed, int) or isinstance(observed, bool) or observed <= 0:
        return reject("missing_or_invalid_observation_time")

    age = getattr(view, "age_ms", None)
    if isinstance(age, bool):
        return reject("invalid_book_age")
    try:
        age_number = float(age)
    except (TypeError, ValueError, OverflowError):
        return reject("invalid_book_age")
    if not math.isfinite(age_number) or age_number < 0:
        return reject("invalid_book_age")
    if age_number > max_age_ms:
        return reject("stale_book")

    if not isinstance(bids, (list, tuple)) or not isinstance(asks, (list, tuple)):
        return reject("invalid_depth_container")
    if not bids or not asks:
        return reject("empty_book_side")
    if bid_count > max_levels_per_side or ask_count > max_levels_per_side:
        return reject("depth_limit_exceeded")

    def prices(levels: tuple | list, *, descending: bool) -> list[tuple[float, float]] | None:
        result: list[tuple[float, float]] = []
        for level in levels:
            try:
                price = float(level.price)
                quantity = float(level.quantity)
            except (AttributeError, TypeError, ValueError, OverflowError):
                return None
            if not math.isfinite(price) or price <= 0 or not math.isfinite(quantity) or quantity <= 0:
                return None
            result.append((price, quantity))
        values = [item[0] for item in result]
        if len(set(values)) != len(values):
            return None
        expected = sorted(values, reverse=descending)
        if values != expected:
            return None
        return result

    bid_values = prices(bids, descending=True)
    ask_values = prices(asks, descending=False)
    if bid_values is None:
        return reject("invalid_or_unsorted_bid_levels")
    if ask_values is None:
        return reject("invalid_or_unsorted_ask_levels")
    if bid_values[0][0] >= ask_values[0][0]:
        return reject("crossed_or_locked_book")

    return L2QualityAssessment(True, "VALID", None, bid_count, ask_count)
