from __future__ import annotations

from typing import Iterable, List, Sequence


def ema(values: Sequence[float], period: int) -> float | None:
    if period <= 0 or len(values) < period:
        return None
    k = 2 / (period + 1)
    result = sum(values[:period]) / period
    for value in values[period:]:
        result = value * k + result * (1 - k)
    return result


def atr(ohlcv: Sequence[Sequence[float]], period: int) -> float | None:
    if period <= 0 or len(ohlcv) < period + 1:
        return None
    ranges: List[float] = []
    for i in range(-period, 0):
        high = float(ohlcv[i][2])
        low = float(ohlcv[i][3])
        prev_close = float(ohlcv[i - 1][4])
        ranges.append(max(high - low, abs(high - prev_close), abs(low - prev_close)))
    return sum(ranges) / period


def vwap(ohlcv: Sequence[Sequence[float]], period: int) -> float | None:
    if period <= 0 or len(ohlcv) < period:
        return None
    selected = ohlcv[-period:]
    volume_sum = sum(float(c[5]) for c in selected)
    if volume_sum <= 0:
        return None
    return sum(((float(c[2]) + float(c[3]) + float(c[4])) / 3) * float(c[5]) for c in selected) / volume_sum


def slope(current: float | None, previous: float | None) -> float:
    if current is None or previous is None or previous == 0:
        return 0.0
    return (current - previous) / previous


def pct_change(current: float, previous: float) -> float:
    if previous == 0:
        return 0.0
    return (current - previous) / previous
