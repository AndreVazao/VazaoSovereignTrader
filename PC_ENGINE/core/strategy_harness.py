from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from typing import Any, Callable, Literal

Action = Literal["BUY", "SELL", "HOLD"]


@dataclass(frozen=True)
class StrategyContext:
    """Read-only PAPER context shared by strategy adapters."""

    symbol: str
    ohlcv: list[list[float]]
    timeframes: dict[str, list[list[float]]]
    regime: str | None = None
    trade_events: list[dict] | None = None


@dataclass(frozen=True)
class StrategyEvidenceRecord:
    """Comparable strategy evidence; never an execution instruction."""

    strategy: str
    action: Action
    score: float
    confidence: float
    reason: str
    metadata: dict[str, Any]
    paper_only: bool = True


class PaperStrategyHarness:
    """Run independent PAPER strategies through one comparable evidence contract.

    The harness is deliberately execution-free. Strategy adapters can only
    produce descriptive evidence. Exceptions fail closed as HOLD evidence so a
    broken strategy cannot become a positive signal by accident.
    """

    def __init__(self) -> None:
        self._strategies: dict[str, Callable[[StrategyContext], Any]] = {}

    def register(self, name: str, evaluator: Callable[[StrategyContext], Any]) -> None:
        normalized = str(name).strip()
        if not normalized:
            raise ValueError("strategy name is required")
        if not callable(evaluator):
            raise TypeError("strategy evaluator must be callable")
        if normalized in self._strategies:
            raise ValueError(f"strategy already registered: {normalized}")
        self._strategies[normalized] = evaluator

    @staticmethod
    def _normalize_action(value: Any) -> Action:
        action = str(value or "HOLD").upper()
        return action if action in {"BUY", "SELL", "HOLD"} else "HOLD"  # type: ignore[return-value]

    @staticmethod
    def _clamp(value: Any) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return 0.0
        if number != number:
            return 0.0
        return max(-1.0, min(1.0, number))

    @staticmethod
    def _confidence(value: Any) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return 0.0
        if number != number:
            return 0.0
        return max(0.0, min(1.0, number))

    @classmethod
    def _normalize(cls, name: str, result: Any) -> StrategyEvidenceRecord:
        action = cls._normalize_action(getattr(result, "action", "HOLD"))
        score = cls._clamp(getattr(result, "score", getattr(result, "strength", 0.0)))
        if action == "BUY":
            score = abs(score)
        elif action == "SELL":
            score = -abs(score)
        else:
            score = 0.0
        confidence = cls._confidence(getattr(result, "confidence", 0.0))
        reason = str(getattr(result, "reason", "") or "")

        if is_dataclass(result):
            raw = asdict(result)
        elif hasattr(result, "__dict__"):
            raw = dict(result.__dict__)
        else:
            raw = {}
        metadata = {
            key: value
            for key, value in raw.items()
            if key not in {"action", "score", "strength", "confidence", "reason"}
        }
        return StrategyEvidenceRecord(
            strategy=name,
            action=action,
            score=round(score, 6),
            confidence=round(confidence, 6),
            reason=reason,
            metadata=metadata,
        )

    def evaluate(self, context: StrategyContext) -> dict[str, StrategyEvidenceRecord]:
        results: dict[str, StrategyEvidenceRecord] = {}
        for name, evaluator in self._strategies.items():
            try:
                results[name] = self._normalize(name, evaluator(context))
            except Exception as exc:
                results[name] = StrategyEvidenceRecord(
                    strategy=name,
                    action="HOLD",
                    score=0.0,
                    confidence=0.0,
                    reason=f"strategy failure: {type(exc).__name__}",
                    metadata={"error": str(exc)},
                )
        return results

    def summary(self, context: StrategyContext) -> dict[str, Any]:
        evidence = self.evaluate(context)
        bullish = sum(1 for item in evidence.values() if item.action == "BUY")
        bearish = sum(1 for item in evidence.values() if item.action == "SELL")
        return {
            "paper_only": True,
            "strategies": {name: item.__dict__ for name, item in evidence.items()},
            "counts": {
                "total": len(evidence),
                "buy": bullish,
                "sell": bearish,
                "hold": len(evidence) - bullish - bearish,
            },
        }
