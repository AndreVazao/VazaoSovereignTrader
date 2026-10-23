from __future__ import annotations

from PC_ENGINE.market_events.binance_book_state import BookStatus, BookSnapshot
from PC_ENGINE.market_events.coinbase_book_sync import CoinbaseBookView
from PC_ENGINE.market_events.depth_edge_adapter import (
    CanonicalInstrumentMapping,
    to_synchronized_book_view,
)
from PC_ENGINE.market_events.orderbook import OrderBookLevel
from PC_ENGINE.radar.depth_edge import assess_synchronized_depth_edge


def _coinbase_view(*, timestamp=1_000_000_000, eligible=True, bids=None, asks=None, symbol="BTC/USD"):
    return CoinbaseBookView(
        venue="coinbase",
        symbol=symbol,
        status="SYNCED",
        sequence=42,
        bids=tuple((OrderBookLevel(100, 1),) if bids is None else bids),
        asks=tuple((OrderBookLevel(101, 1),) if asks is None else asks),
        age_ms=0.0,
        eligible=eligible,
        reason=None,
        observation_time_ns=timestamp,
        price_unit="USD" if symbol.endswith("/USD") else "USDT",
    )


def test_adapter_recomputes_age_from_shared_monotonic_timestamp():
    mapping = CanonicalInstrumentMapping("coinbase", "BTC/USD", "spot:BTC/USD", "USD")
    view = to_synchronized_book_view(mapping, _coinbase_view(), now_ns=1_100_000_000)
    assert view.eligible is True
    assert view.age_ms == 100.0
    assert view.observation_time_ns == 1_000_000_000


def test_adapter_refuses_old_callback_even_if_it_was_eligible_when_emitted():
    mapping = CanonicalInstrumentMapping("coinbase", "BTC/USD", "spot:BTC/USD", "USD")
    view = to_synchronized_book_view(
        mapping, _coinbase_view(), now_ns=2_000_000_000, max_age_ms=250,
    )
    assert view.eligible is False
    assert view.status == "SYNCED"
    assert view.best_bid is None


def test_adapter_refuses_symbol_or_venue_mapping_mismatch():
    mapping = CanonicalInstrumentMapping("coinbase", "BTC/USD", "spot:BTC/USD", "USD")
    wrong = _coinbase_view()
    wrong = CoinbaseBookView(
        venue="coinbase", symbol="ETH/USD", status="SYNCED", sequence=42,
        bids=wrong.bids, asks=wrong.asks, age_ms=0, eligible=True, reason=None,
        observation_time_ns=1_000_000_000,
    )
    view = to_synchronized_book_view(mapping, wrong, now_ns=1_010_000_000)
    assert view.eligible is False
    assert view.status == "INVALID"


def test_adapter_rejects_crossed_or_one_sided_book():
    mapping = CanonicalInstrumentMapping("coinbase", "BTC/USD", "spot:BTC/USD", "USD")
    crossed = _coinbase_view(
        bids=(OrderBookLevel(102, 1),), asks=(OrderBookLevel(101, 1),),
    )
    assert not to_synchronized_book_view(mapping, crossed, now_ns=1_010_000_000).eligible
    one_sided = _coinbase_view(asks=())
    assert not to_synchronized_book_view(mapping, one_sided, now_ns=1_010_000_000).eligible


def test_adapter_supports_binance_snapshot_and_depth_edge_assessment():
    now_ns = 1_100_000_000
    left = BookSnapshot(
        status=BookStatus.SYNCED, update_id=100,
        bids=(OrderBookLevel(100, 2),), asks=(OrderBookLevel(100.1, 2),),
        age_ms=100.0, eligible=True, reason=None, observation_time_ns=1_000_000_000,
    )
    right = _coinbase_view(timestamp=1_050_000_000, symbol="BTC/USDT",
                           bids=(OrderBookLevel(101, 2),),
                           asks=(OrderBookLevel(101.1, 2),))
    left_view = to_synchronized_book_view(
        CanonicalInstrumentMapping("binance", "BTC/USDT", "spot:BTC/USDT", "USDT"),
        left, now_ns=now_ns,
    )
    right_view = to_synchronized_book_view(
        CanonicalInstrumentMapping("coinbase", "BTC/USDT", "spot:BTC/USDT", "USDT"),
        right, now_ns=now_ns,
    )
    # Canonical identity must be provided by an independently validated map;
    # the adapter does not infer that BTC/USDT and BTC/USD are equivalent.
    assessment = assess_synchronized_depth_edge(
        left_view, right_view,
        venue_costs_bps={"binance": 2, "coinbase": 2},
        max_observation_skew_ms=100,
    )
    assert assessment.eligible is True
    assert assessment.observation_skew_ms == 50.0



def test_adapter_preserves_distinct_quote_price_units_for_edge_rejection():
    now_ns = 1_100_000_000
    left = BookSnapshot(
        status=BookStatus.SYNCED, update_id=100,
        bids=(OrderBookLevel(100, 2),), asks=(OrderBookLevel(100.1, 2),),
        age_ms=100.0, eligible=True, reason=None, observation_time_ns=1_000_000_000,
    )
    right = _coinbase_view(timestamp=1_050_000_000)
    left_view = to_synchronized_book_view(
        CanonicalInstrumentMapping("binance", "BTC/USDT", "same-id-misconfigured", "USDT"),
        left, now_ns=now_ns,
    )
    right_view = to_synchronized_book_view(
        CanonicalInstrumentMapping("coinbase", "BTC/USD", "same-id-misconfigured", "USD"),
        right, now_ns=now_ns,
    )
    assessment = assess_synchronized_depth_edge(
        left_view, right_view,
        venue_costs_bps={"binance": 2, "coinbase": 2},
        max_observation_skew_ms=100,
    )
    assert assessment.eligible is False
    assert assessment.reason == "price_unit_mismatch"


def test_adapter_validates_age_limit_and_monotonic_now():
    mapping = CanonicalInstrumentMapping("coinbase", "BTC/USD", "spot:BTC/USD", "USD")
    import pytest
    with pytest.raises(ValueError):
        to_synchronized_book_view(mapping, _coinbase_view(), now_ns=1, max_age_ms=float("nan"))
    with pytest.raises(ValueError):
        to_synchronized_book_view(mapping, _coinbase_view(), now_ns=True)
