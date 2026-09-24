from PC_ENGINE.core.preflight import validate_market_candles
from PC_ENGINE.tools.run_readiness_pipeline import run_execution_smoke_test


def test_paper_execution_smoke_test_passes():
    result = run_execution_smoke_test()

    assert result["paper_only"] is True
    assert result["ok"] is True
    assert result["passed"] is True
    assert result["checks"] == {
        "paper_fill": True,
        "duplicate_block": True,
        "invalid_order_block": True,
    }


def test_market_data_quality_accepts_ordered_valid_ohlcv():
    result = validate_market_candles(
        [
            {"timestamp": 1000, "open": 100, "high": 102, "low": 99, "close": 101, "volume": 10},
            {"timestamp": 1060, "open": 101, "high": 103, "low": 100, "close": 102, "volume": 12},
            {"timestamp": 1120, "open": 102, "high": 104, "low": 101, "close": 103, "volume": 9},
        ],
        max_gap_seconds=60,
    )

    assert result.ok is True
    assert result.errors == []
    assert result.valid_rows == 3


def test_market_data_quality_rejects_duplicates_gaps_and_impossible_prices():
    duplicate = validate_market_candles(
        [
            {"timestamp": 1000, "open": 100, "high": 102, "low": 99, "close": 101, "volume": 10},
            {"timestamp": 1000, "open": 101, "high": 103, "low": 100, "close": 102, "volume": 12},
        ]
    )
    assert duplicate.ok is False
    assert "duplicate timestamp" in duplicate.errors[0]

    gap = validate_market_candles(
        [
            {"timestamp": 1000, "open": 100, "high": 102, "low": 99, "close": 101, "volume": 10},
            {"timestamp": 1121, "open": 101, "high": 103, "low": 100, "close": 102, "volume": 12},
        ],
        max_gap_seconds=60,
    )
    assert gap.ok is False
    assert "timestamp gap" in gap.errors[0]

    impossible = validate_market_candles(
        [
            {"timestamp": 1000, "open": 100, "high": 99, "low": 98, "close": 101, "volume": 10},
        ]
    )
    assert impossible.ok is False
    assert "impossible high price" in impossible.errors[0]


def test_market_data_quality_rejects_non_finite_and_negative_values():
    non_finite = validate_market_candles(
        [
            {"timestamp": 1000, "open": float("nan"), "high": 102, "low": 99, "close": 101, "volume": 10},
        ]
    )
    assert non_finite.ok is False
    assert "non-finite market data" in non_finite.errors[0]

    negative_volume = validate_market_candles(
        [
            {"timestamp": 1000, "open": 100, "high": 102, "low": 99, "close": 101, "volume": -1},
        ]
    )
    assert negative_volume.ok is False
    assert "negative volume" in negative_volume.errors[0]
