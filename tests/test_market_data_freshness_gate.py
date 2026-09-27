from PC_ENGINE.core.preflight import validate_ohlcv_rows


def candle(ts, o=100.0, h=101.0, l=99.0, c=100.5, v=10.0):
    return [ts, o, h, l, c, v]


def test_market_data_freshness_accepts_recent_timestamp():
    result = validate_ohlcv_rows(
        [candle(99_940), candle(99_960)],
        max_age_seconds=120,
        now_seconds=100_000,
    )
    assert result.ok is True
    assert result.valid_rows == 2


def test_market_data_freshness_blocks_stale_timestamp():
    result = validate_ohlcv_rows(
        [candle(99_700), candle(99_750)],
        max_age_seconds=120,
        now_seconds=100_000,
    )
    assert result.ok is False
    assert any("age" in error for error in result.errors)


def test_market_data_freshness_blocks_future_timestamp():
    result = validate_ohlcv_rows(
        [candle(100_000), candle(100_010)],
        max_age_seconds=120,
        now_seconds=100_000,
    )
    assert result.ok is False
    assert any("future" in error for error in result.errors)


def test_market_data_quality_remains_fail_closed_for_gap_and_invalid_ohlc():
    result = validate_ohlcv_rows(
        [
            candle(100_000),
            candle(100_300, o=100, h=99, l=98, c=98.5),
        ],
        max_gap_seconds=180,
        max_age_seconds=120,
        now_seconds=100_000,
    )
    assert result.ok is False
    assert any("gap" in error for error in result.errors)
    assert any("impossible high" in error for error in result.errors)
