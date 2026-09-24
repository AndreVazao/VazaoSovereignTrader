from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, List, Mapping


@dataclass
class MarketDataQualityResult:
    ok: bool
    errors: List[str]
    warnings: List[str]
    valid_rows: int


def validate_market_candles(
    candles: Iterable[Mapping[str, object]],
    *,
    max_gap_seconds: float | None = None,
) -> MarketDataQualityResult:
    """Fail-closed validation for OHLCV candles before strategy consumption."""
    errors: List[str] = []
    warnings: List[str] = []
    rows = list(candles)

    if not rows:
        return MarketDataQualityResult(
            ok=False,
            errors=["no market data rows"],
            warnings=[],
            valid_rows=0,
        )

    previous_timestamp: float | None = None
    seen_timestamps: set[float] = set()
    valid_rows = 0

    for index, row in enumerate(rows):
        prefix = f"row {index}"
        required = ("timestamp", "open", "high", "low", "close", "volume")
        missing = [field for field in required if field not in row]
        if missing:
            errors.append(f"{prefix}: missing fields: {','.join(missing)}")
            continue

        try:
            timestamp = float(row["timestamp"])
            open_price = float(row["open"])
            high_price = float(row["high"])
            low_price = float(row["low"])
            close_price = float(row["close"])
            volume = float(row["volume"])
        except (TypeError, ValueError):
            errors.append(f"{prefix}: non-numeric market data")
            continue

        if not all(
            math.isfinite(value)
            for value in (
                timestamp,
                open_price,
                high_price,
                low_price,
                close_price,
                volume,
            )
        ):
            errors.append(f"{prefix}: non-finite market data")
            continue

        # Accept common millisecond timestamps while keeping gap checks in seconds.
        normalized_timestamp = (
            timestamp / 1000.0 if abs(timestamp) >= 1e11 else timestamp
        )
        if normalized_timestamp in seen_timestamps:
            errors.append(f"{prefix}: duplicate timestamp")
            continue
        seen_timestamps.add(normalized_timestamp)

        if previous_timestamp is not None:
            delta = normalized_timestamp - previous_timestamp
            if delta <= 0:
                errors.append(f"{prefix}: non-increasing timestamp")
                continue
            if max_gap_seconds is not None and delta > max_gap_seconds:
                errors.append(
                    f"{prefix}: timestamp gap {delta:g}s exceeds {max_gap_seconds:g}s"
                )
                continue
        previous_timestamp = normalized_timestamp

        if min(open_price, high_price, low_price, close_price) <= 0:
            errors.append(f"{prefix}: non-positive OHLC price")
            continue
        if high_price < max(open_price, close_price, low_price):
            errors.append(f"{prefix}: impossible high price")
            continue
        if low_price > min(open_price, close_price, high_price):
            errors.append(f"{prefix}: impossible low price")
            continue
        if volume < 0:
            errors.append(f"{prefix}: negative volume")
            continue

        valid_rows += 1

    return MarketDataQualityResult(
        ok=not errors,
        errors=errors,
        warnings=warnings,
        valid_rows=valid_rows,
    )
