from __future__ import annotations

from dataclasses import dataclass
from time import monotonic_ns
from typing import Callable, Iterable, Mapping


@dataclass(frozen=True)
class FastPathSignal:
    symbol: str
    leader: str
    follower: str
    direction: str
    horizon_ms: int
    expectancy_bps: float
    confidence: float
    samples: int


@dataclass(frozen=True)
class FastPathDecision:
    accepted: bool
    reason: str
    symbol: str = ""
    direction: str = ""
    leader: str = ""
    follower: str = ""
    horizon_ms: int = 0
    expectancy_bps: float = 0.0
    confidence: float = 0.0
    age_ms: int = 0
    evaluation_ns: int = 0


class FastPathEngine:
    """Small deterministic decision path for already-learned opportunities.

    This layer is deliberately independent from the slow learning pipeline.
    It never places an order and never calls an LLM. A caller supplies the
    final risk/execution authorization callback.
    """

    def __init__(
        self,
        min_confidence: float = 0.75,
        min_expectancy_bps: float = 2.0,
        max_signal_age_ms: int = 1000,
    ) -> None:
        self.min_confidence = float(min_confidence)
        self.min_expectancy_bps = float(min_expectancy_bps)
        self.max_signal_age_ms = max(1, int(max_signal_age_ms))

    @staticmethod
    def _index(signals: Iterable[FastPathSignal]) -> dict[tuple[str, str, str], FastPathSignal]:
        indexed: dict[tuple[str, str, str], FastPathSignal] = {}
        for signal in signals:
            key = (signal.symbol.upper(), signal.leader.lower(), signal.follower.lower())
            current = indexed.get(key)
            if current is None or (signal.confidence, signal.expectancy_bps, signal.samples) > (
                current.confidence, current.expectancy_bps, current.samples
            ):
                indexed[key] = signal
        return indexed

    def evaluate(
        self,
        event: Mapping[str, object],
        signals: Iterable[FastPathSignal],
        *,
        now_ms: int,
        risk_check: Callable[[FastPathSignal, Mapping[str, object]], bool] | None = None,
    ) -> FastPathDecision:
        started = monotonic_ns()
        symbol = str(event.get("symbol", "")).upper()
        exchange = str(event.get("exchange", "")).lower()
        timestamp = int(event.get("timestamp_ms", event.get("exchange_ts_ms", now_ms)))
        age = max(0, int(now_ms) - timestamp)

        if not symbol or not exchange:
            return self._reject("invalid_event", started)
        if age > self.max_signal_age_ms:
            return self._reject("stale_event", started, symbol=symbol, age_ms=age)

        direction = str(event.get("direction", "")).upper()
        if direction not in {"UP", "DOWN", "BUY", "SELL"}:
            return self._reject("invalid_direction", started, symbol=symbol, age_ms=age)
        direction = "UP" if direction in {"UP", "BUY"} else "DOWN"

        indexed = self._index(signals)
        candidates = [
            signal for (candidate_symbol, leader, follower), signal in indexed.items()
            if candidate_symbol == symbol and follower == exchange
            and signal.direction.upper() == direction
            and signal.confidence >= self.min_confidence
            and signal.expectancy_bps >= self.min_expectancy_bps
            and leader != follower
        ]
        if not candidates:
            return self._reject("no_validated_opportunity", started, symbol=symbol, age_ms=age)

        signal = max(candidates, key=lambda item: (item.expectancy_bps, item.confidence, item.samples))
        if risk_check is not None and not risk_check(signal, event):
            return self._reject("risk_rejected", started, symbol=symbol, age_ms=age, signal=signal)

        return FastPathDecision(
            accepted=True,
            reason="validated_fast_path",
            symbol=symbol,
            direction=direction,
            leader=signal.leader,
            follower=signal.follower,
            horizon_ms=signal.horizon_ms,
            expectancy_bps=signal.expectancy_bps,
            confidence=signal.confidence,
            age_ms=age,
            evaluation_ns=monotonic_ns() - started,
        )

    def _reject(self, reason: str, started: int, *, symbol: str = "", age_ms: int = 0,
                signal: FastPathSignal | None = None) -> FastPathDecision:
        return FastPathDecision(
            accepted=False,
            reason=reason,
            symbol=symbol,
            leader=signal.leader if signal else "",
            follower=signal.follower if signal else "",
            horizon_ms=signal.horizon_ms if signal else 0,
            expectancy_bps=signal.expectancy_bps if signal else 0.0,
            confidence=signal.confidence if signal else 0.0,
            age_ms=age_ms,
            evaluation_ns=monotonic_ns() - started,
        )


def load_fast_signals(rows: Iterable[Mapping[str, object]]) -> tuple[FastPathSignal, ...]:
    """Convert persisted lead/lag rows into immutable fast-path records."""
    result: list[FastPathSignal] = []
    for row in rows:
        if not bool(row.get("eligible")):
            continue
        try:
            result.append(FastPathSignal(
                symbol=str(row["symbol"]),
                leader=str(row["leader"]),
                follower=str(row["follower"]),
                direction=str(row["direction"]),
                horizon_ms=int(row["horizon_ms"]),
                expectancy_bps=float(row["expectancy_bps"]),
                confidence=float(row["confidence"]),
                samples=int(row["samples"]),
            ))
        except (KeyError, TypeError, ValueError):
            continue
    return tuple(result)
