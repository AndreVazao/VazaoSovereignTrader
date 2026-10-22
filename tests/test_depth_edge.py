import pytest

from PC_ENGINE.radar.depth_edge import (
    SynchronizedBookView,
    assess_synchronized_depth_edge,
)


def book(venue, bid, ask, *, age=20.0, eligible=True, status="SYNCED", instrument="spot:BTC/USDT"):
    return SynchronizedBookView(
        venue=venue,
        instrument_id=instrument,
        status=status,
        eligible=eligible,
        age_ms=age,
        best_bid=bid,
        best_ask=ask,
    )


def test_assesses_positive_net_edge_after_both_venue_costs():
    result = assess_synchronized_depth_edge(
        book("binance", 100.0, 100.1),
        book("coinbase", 101.0, 101.1),
        venue_costs_bps={"binance": 2.0, "coinbase": 3.0},
        latency_penalty_bps=1.0,
        min_net_edge_bps=10.0,
    )
    assert result.eligible is True
    assert result.reason == "net_edge_above_threshold"
    assert result.buy_venue == "binance"
    assert result.sell_venue == "coinbase"
    assert result.net_edge_bps == pytest.approx((101.0 - 100.1) / 100.1 * 10_000 - 6.0)
    assert result.paper_only is True
    assert result.execution_allowed is False


def test_rejects_different_canonical_instruments():
    result = assess_synchronized_depth_edge(
        book("binance", 100, 100.1),
        book("coinbase", 101, 101.1, instrument="perpetual:BTC/USDT"),
        venue_costs_bps={"binance": 1, "coinbase": 1},
    )
    assert result.eligible is False
    assert result.reason == "instrument_mismatch"


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"status": "INVALID"}, "book_not_synchronized"),
        ({"eligible": False}, "book_not_synchronized"),
        ({"age": 251.0}, "stale_book"),
        ({"age": float("nan")}, "invalid_book_age"),
        ({"bid": 101.0}, "invalid_or_crossed_book"),
        ({"ask": 0.0}, "invalid_or_crossed_book"),
    ],
)
def test_rejects_unusable_book_views(changes, reason):
    left = book("binance", 100, 100.1)
    values = {"bid": left.best_bid, "ask": left.best_ask, "age": left.age_ms,
              "eligible": left.eligible, "status": left.status}
    values.update(changes)
    left = book("binance", values["bid"], values["ask"], age=values["age"],
                eligible=values["eligible"], status=values["status"])
    result = assess_synchronized_depth_edge(
        left, book("coinbase", 101, 101.1),
        venue_costs_bps={"binance": 1, "coinbase": 1},
    )
    assert result.eligible is False
    assert result.reason == reason


def test_costs_can_remove_apparent_gross_edge():
    result = assess_synchronized_depth_edge(
        book("binance", 100.0, 100.1),
        book("coinbase", 100.2, 100.3),
        venue_costs_bps={"binance": 5.0, "coinbase": 5.0},
        latency_penalty_bps=2.0,
        min_net_edge_bps=0.0,
    )
    assert result.eligible is False
    assert result.reason == "net_edge_below_threshold"
    assert result.net_edge_bps < 0


def test_rejects_missing_cost_assumptions_and_invalid_configuration():
    result = assess_synchronized_depth_edge(
        book("binance", 100, 100.1),
        book("coinbase", 101, 101.1),
        venue_costs_bps={"binance": 1},
    )
    assert result.reason == "missing_venue_cost_assumption"
    with pytest.raises(ValueError):
        assess_synchronized_depth_edge(
            book("binance", 100, 100.1),
            book("coinbase", 101, 101.1),
            venue_costs_bps={"binance": 1, "coinbase": float("inf")},
        )
