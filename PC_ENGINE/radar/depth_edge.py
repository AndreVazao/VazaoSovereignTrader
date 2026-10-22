from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping


@dataclass(frozen=True)
class SynchronizedBookView:
    """Minimal normalized view supplied by a venue-specific book synchronizer.

    instrument_id must be a canonical identity produced by a separately
    validated market-mapping layer (for example, spot BTC/USDT, not a raw
    venue symbol). This module does not infer equivalence between instruments.
    """

    venue: str
    instrument_id: str
    status: str
    eligible: bool
    age_ms: float | None
    best_bid: float | None
    best_ask: float | None
    sequence: int | str | None = None


@dataclass(frozen=True)
class DepthEdgeAssessment:
    eligible: bool
    reason: str
    buy_venue: str | None = None
    sell_venue: str | None = None
    instrument_id: str | None = None
    gross_edge_bps: float | None = None
    net_edge_bps: float | None = None
    buy_book_age_ms: float | None = None
    sell_book_age_ms: float | None = None
    paper_only: bool = True
    execution_allowed: bool = False


def _finite_non_negative(name: str, value: float) -> float:
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"{name} must be finite and non-negative")
    return number


def _reject(reason: str, left: SynchronizedBookView,
            right: SynchronizedBookView) -> DepthEdgeAssessment:
    return DepthEdgeAssessment(
        eligible=False,
        reason=reason,
        instrument_id=left.instrument_id if left.instrument_id == right.instrument_id else None,
        buy_book_age_ms=left.age_ms,
        sell_book_age_ms=right.age_ms,
    )


def assess_synchronized_depth_edge(
    left: SynchronizedBookView,
    right: SynchronizedBookView,
    *,
    venue_costs_bps: Mapping[str, float],
    latency_penalty_bps: float = 0.0,
    min_net_edge_bps: float = 0.0,
    max_age_ms: float = 250.0,
) -> DepthEdgeAssessment:
    """Compare synchronized top-of-book views for PAPER research only.

    venue_costs_bps is the estimated fee plus slippage cost for one leg at
    each venue. The total cross-venue cost includes both legs plus latency.
    This function does not fetch data, normalize symbols, estimate fill
    probability, or authorize/submit orders.
    """
    latency_penalty = _finite_non_negative("latency_penalty_bps", latency_penalty_bps)
    min_net = _finite_non_negative("min_net_edge_bps", min_net_edge_bps)
    max_age = _finite_non_negative("max_age_ms", max_age_ms)
    if max_age <= 0:
        raise ValueError("max_age_ms must be positive")

    if not left.venue.strip() or not right.venue.strip() or left.venue.lower() == right.venue.lower():
        return _reject("distinct_venues_required", left, right)
    if not left.instrument_id.strip() or left.instrument_id != right.instrument_id:
        return _reject("instrument_mismatch", left, right)

    for view in (left, right):
        if view.status != "SYNCED" or view.eligible is not True:
            return _reject("book_not_synchronized", left, right)
        try:
            age = float(view.age_ms)
        except (TypeError, ValueError, OverflowError):
            return _reject("invalid_book_age", left, right)
        if not math.isfinite(age) or age < 0:
            return _reject("invalid_book_age", left, right)
        if age > max_age:
            return _reject("stale_book", left, right)
        if view.best_bid is None or view.best_ask is None:
            return _reject("missing_top_of_book", left, right)
        try:
            bid, ask = float(view.best_bid), float(view.best_ask)
        except (TypeError, ValueError, OverflowError):
            return _reject("invalid_or_crossed_book", left, right)
        if not math.isfinite(bid) or not math.isfinite(ask) or bid <= 0 or ask <= 0 or bid >= ask:
            return _reject("invalid_or_crossed_book", left, right)

    if left.venue not in venue_costs_bps or right.venue not in venue_costs_bps:
        return _reject("missing_venue_cost_assumption", left, right)
    left_cost = _finite_non_negative(f"{left.venue}_cost_bps", venue_costs_bps[left.venue])
    right_cost = _finite_non_negative(f"{right.venue}_cost_bps", venue_costs_bps[right.venue])
    total_cost = left_cost + right_cost + latency_penalty
    if not math.isfinite(total_cost):
        raise ValueError("combined cost assumptions must be finite")

    candidates = (
        (left, right, float(left.best_ask), float(right.best_bid)),
        (right, left, float(right.best_ask), float(left.best_bid)),
    )
    assessments: list[DepthEdgeAssessment] = []
    for buy, sell, entry, exit_price in candidates:
        gross = (exit_price - entry) / entry * 10_000.0
        net = gross - total_cost
        is_eligible = math.isfinite(net) and net > min_net
        assessments.append(DepthEdgeAssessment(
            eligible=is_eligible,
            reason="net_edge_above_threshold" if is_eligible else "net_edge_below_threshold",
            buy_venue=buy.venue,
            sell_venue=sell.venue,
            instrument_id=left.instrument_id,
            gross_edge_bps=gross,
            net_edge_bps=net,
            buy_book_age_ms=buy.age_ms,
            sell_book_age_ms=sell.age_ms,
        ))

    best = max(assessments, key=lambda item: item.net_edge_bps if item.net_edge_bps is not None else -math.inf)
    if best.eligible:
        return best
    return DepthEdgeAssessment(
        eligible=False,
        reason="net_edge_below_threshold",
        buy_venue=best.buy_venue,
        sell_venue=best.sell_venue,
        instrument_id=best.instrument_id,
        gross_edge_bps=best.gross_edge_bps,
        net_edge_bps=best.net_edge_bps,
        buy_book_age_ms=best.buy_book_age_ms,
        sell_book_age_ms=best.sell_book_age_ms,
    )
