from __future__ import annotations

import pytest

from PC_ENGINE.backtest.replay import ReplayBacktester
from PC_ENGINE.core.preflight import validate_ohlcv_rows


def _candles(count: int = 61) -> list[list[float]]:
    rows = []
    for index in range(count):
        timestamp = 1_700_000_000_000 + index * 60_000
        price = 100.0 + index * 0.05
        rows.append([timestamp, price, price + 0.5, price - 0.5, price + 0.1, 10.0])
    return rows


def test_ccxt_rows_pass_quality_gate() -> None:
    result = validate_ohlcv_rows(_candles())
    assert result.ok
    assert result.valid_rows == 61
    assert result.errors == []


def test_malformed_ccxt_row_is_fail_closed() -> None:
    candles = _candles()
    candles[20] = candles[20][:5]

    result = validate_ohlcv_rows(candles)

    assert not result.ok
    assert result.valid_rows == 0
    assert any("expected 6 OHLCV fields" in error for error in result.errors)


def test_gap_is_fail_closed_when_configured() -> None:
    candles = _candles()
    candles[30][0] += 10 * 60_000

    result = validate_ohlcv_rows(candles, max_gap_seconds=120)

    assert not result.ok
    assert any("timestamp gap" in error for error in result.errors)


def test_backtest_rejects_invalid_market_data() -> None:
    candles = _candles()
    candles[10][4] = 0.0

    class Strategy:
        def analyse(self, *args, **kwargs):
            raise AssertionError("strategy must not receive invalid candles")

    with pytest.raises(ValueError, match="market data quality gate rejected"):
        ReplayBacktester(Strategy()).run("BTC/USDT", candles)
