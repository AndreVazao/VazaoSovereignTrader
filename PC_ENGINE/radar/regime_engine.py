from __future__ import annotations

from dataclasses import dataclass
from statistics import fmean


@dataclass(frozen=True)
class MarketRegime:
    name: str
    trend: str
    volatility: str
    confidence: float


class MarketRegimeEngine:
    """Small deterministic regime classifier for lead/lag segmentation.

    This is descriptive only. It never creates or authorizes an order.
    """

    def __init__(self, trend_threshold: float = 0.0015, high_volatility: float = 0.004,
                 low_volatility: float = 0.0008) -> None:
        self.trend_threshold = abs(float(trend_threshold))
        self.high_volatility = abs(float(high_volatility))
        self.low_volatility = abs(float(low_volatility))

    def classify(self, returns: list[float]) -> MarketRegime:
        if not returns:
            return MarketRegime("UNKNOWN", "FLAT", "UNKNOWN", 0.0)
        mean_return = fmean(returns)
        # For return series, use RMS magnitude as the realized movement level.
        # Unlike dispersion around the mean, this still marks a consistently
        # directional high-magnitude regime as HIGH volatility.
        volatility = (fmean([x * x for x in returns])) ** 0.5
        if mean_return > self.trend_threshold:
            trend = "UP"
        elif mean_return < -self.trend_threshold:
            trend = "DOWN"
        else:
            trend = "FLAT"
        if volatility >= self.high_volatility:
            vol = "HIGH"
        elif volatility <= self.low_volatility:
            vol = "LOW"
        else:
            vol = "NORMAL"
        confidence = min(1.0, len(returns) / 20.0)
        return MarketRegime(f"{trend}_{vol}", trend, vol, round(confidence, 4))
