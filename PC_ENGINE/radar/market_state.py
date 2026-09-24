from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import time
from pathlib import Path

from PC_ENGINE.core.retention import retain_jsonl


@dataclass(frozen=True)
class MarketState:
    symbol: str
    timestamp_ms: int
    price: float
    regime: str
    trend: str
    volatility: str
    regime_confidence: float
    technical_score: float
    candlestick_bias: float
    radar_pressure: float
    lead_lag_score: float
    momentum_score: float
    mean_reversion_score: float
    order_flow_score: float
    breakout_score: float
    derivatives_score: float
    confluence_score: float
    confluence_confidence: float
    action: str
    strategy_evidence: dict[str, dict] | None = None

    def to_dict(self) -> dict:
        return asdict(self)


class MarketStateStore:
    """Append-only PAPER observation store for unified market states."""

    def __init__(self, data_dir: str = "PC_ENGINE/data/radar", filename: str = "market_states.jsonl", *, max_rows: int = 100_000, max_age_days: int = 14, compact_every: int = 2_000) -> None:
        self.path = Path(data_dir) / filename
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.max_rows = max(1_000, int(max_rows))
        self.max_age_ms = max(1, int(max_age_days)) * 86_400_000
        self.compact_every = max(100, int(compact_every))
        self._append_count = 0

    def append(self, state: MarketState) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(state.to_dict(), separators=(",", ":"), sort_keys=True) + "\n")

    def recent(self, symbol: str | None = None, limit: int = 500) -> list[dict]:
        limit = max(1, int(limit))
        if not self.path.exists():
            return []
        rows: list[dict] = []
        with self.path.open("rb") as handle:
            for raw in handle.readlines()[-max(limit * 3, 1000):]:
                try:
                    row = json.loads(raw.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    continue
                if symbol is not None and row.get("symbol") != symbol:
                    continue
                rows.append(row)
        return rows[-limit:]

    def snapshot(self, symbol: str) -> dict | None:
        rows = self.recent(symbol, 1)
        return rows[0] if rows else None


def build_market_state(
    *,
    symbol: str,
    price: float,
    regime,
    technical_score: float,
    candlestick_bias: float,
    radar_pressure: float,
    lead_lag_score: float,
    momentum_score: float,
    mean_reversion_score: float,
    order_flow_score: float,
    breakout_score: float,
    derivatives_score: float,
    confluence,
    strategy_evidence: dict[str, dict] | None = None,
    timestamp_ms: int | None = None,
) -> MarketState:
    """Create a normalized immutable state from independent evidence sources."""
    def clamp(value: float) -> float:
        return max(-1.0, min(1.0, float(value)))

    return MarketState(
        symbol=symbol,
        timestamp_ms=int(time.time() * 1000) if timestamp_ms is None else int(timestamp_ms),
        price=float(price),
        regime=str(regime.name),
        trend=str(regime.trend),
        volatility=str(regime.volatility),
        regime_confidence=max(0.0, min(1.0, float(regime.confidence))),
        technical_score=clamp(technical_score),
        candlestick_bias=clamp(candlestick_bias),
        radar_pressure=clamp(radar_pressure),
        lead_lag_score=clamp(lead_lag_score),
        momentum_score=clamp(momentum_score),
        mean_reversion_score=clamp(mean_reversion_score),
        order_flow_score=clamp(order_flow_score),
        breakout_score=clamp(breakout_score),
        derivatives_score=clamp(derivatives_score),
        confluence_score=clamp(confluence.score),
        confluence_confidence=max(0.0, min(1.0, float(confluence.confidence))),
        action=str(confluence.action),
        strategy_evidence=dict(strategy_evidence or {}),
    )
