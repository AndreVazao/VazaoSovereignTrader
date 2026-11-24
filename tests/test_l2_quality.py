from __future__ import annotations

from types import SimpleNamespace

import pytest

from PC_ENGINE.market_events.l2_quality import assess_l2_book_view
from PC_ENGINE.market_events.orderbook import OrderBookLevel
from PC_ENGINE.tools.run_l2_market_data_collector import synchronized_book_payload


def valid_view(**changes):
    values = {
        "venue": "binance",
        "symbol": "BTC/USDT",
        "status": "SYNCED",
        "sequence": 42,
        "bids": (OrderBookLevel(100.0, 2.0), OrderBookLevel(99.0, 1.0)),
        "asks": (OrderBookLevel(101.0, 3.0), OrderBookLevel(102.0, 1.0)),
        "age_ms": 12.0,
        "eligible": True,
        "reason": None,
        "observation_time_ns": 1_000_000_000,
    }
    values.update(changes)
    return SimpleNamespace(**values)


def test_accepts_synchronized_fresh_ordered_book():
    result = assess_l2_book_view(valid_view())
    assert result.analysis_eligible is True
    assert result.quality_status == "VALID"
    assert result.quality_reason is None
    assert result.bid_levels == 2
    assert result.ask_levels == 2


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"status": "INVALID"}, "book_not_synchronized"),
        ({"eligible": False, "reason": "sequence_gap"}, "sequence_gap"),
        ({"sequence": True}, "missing_or_invalid_sequence"),
        ({"observation_time_ns": None}, "missing_or_invalid_observation_time"),
        ({"age_ms": float("nan")}, "invalid_book_age"),
        ({"age_ms": 1001.0}, "stale_book"),
        ({"bids": ()}, "empty_book_side"),
        ({"bids": (OrderBookLevel(99, 1), OrderBookLevel(100, 1))}, "invalid_or_unsorted_bid_levels"),
        ({"asks": (OrderBookLevel(102, 1), OrderBookLevel(101, 1))}, "invalid_or_unsorted_ask_levels"),
        ({"bids": (OrderBookLevel(100, 1), OrderBookLevel(100, 2))}, "invalid_or_unsorted_bid_levels"),
        ({"bids": (OrderBookLevel(101, 1),)}, "crossed_or_locked_book"),
        ({"asks": (OrderBookLevel(100, 1),)}, "crossed_or_locked_book"),
        ({"asks": (OrderBookLevel(101, 0),)}, "invalid_or_unsorted_ask_levels"),
    ],
)
def test_flags_unusable_books(changes, reason):
    result = assess_l2_book_view(valid_view(**changes))
    assert result.analysis_eligible is False
    assert result.quality_status == "FLAGGED"
    assert result.quality_reason == reason


def test_flags_excessive_depth_without_truncating_raw_book():
    bids = tuple(OrderBookLevel(2000 - index, 1) for index in range(5001))
    result = assess_l2_book_view(valid_view(bids=bids))
    assert result.analysis_eligible is False
    assert result.quality_reason == "depth_limit_exceeded"
    assert result.bid_levels == 5001


def test_synchronized_payload_preserves_raw_book_and_adds_quality_metadata():
    view = valid_view(eligible=False, reason="sequence_gap")
    payload = synchronized_book_payload("binance", "BTC/USDT", view)
    assert payload["analysis_eligible"] is False
    assert payload["quality_status"] == "FLAGGED"
    assert payload["quality_reason"] == "sequence_gap"
    assert len(payload["bids"]) == 2
    assert payload["paper_only"] is True
    assert payload["orders_submitted"] is False


def test_quality_configuration_must_be_valid():
    with pytest.raises(ValueError, match="invalid_max_age_ms"):
        assess_l2_book_view(valid_view(), max_age_ms=float("inf"))
    with pytest.raises(ValueError, match="invalid_max_levels_per_side"):
        assess_l2_book_view(valid_view(), max_levels_per_side=True)
