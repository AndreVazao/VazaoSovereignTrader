from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PaperLeadLagSignal:
    symbol: str
    leader: str
    follower: str
    direction: str
    horizon_ms: int
    expectancy_bps: float
    confidence: float
    samples: int
    regime: str = "UNKNOWN"
    paper_only: bool = True


class LeadLagSignalEngine:
    """Turns validated learned statistics into descriptive PAPER signals only."""

    def __init__(self, data_dir: str | Path = "PC_ENGINE/data/radar") -> None:
        self.data_dir = Path(data_dir)

    def load(self) -> list[dict[str, Any]]:
        path = self.data_dir / "lead_lag_learning.json"
        if not path.exists():
            return []
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                return []
            rows = payload.get("stats", [])
            if not isinstance(rows, list):
                return []
            return [row for row in rows if isinstance(row, dict)]
        except (OSError, json.JSONDecodeError):
            return []

    @staticmethod
    def _text(row: dict[str, Any], key: str) -> str | None:
        value = row.get(key)
        if not isinstance(value, str):
            return None
        value = value.strip()
        return value or None

    @staticmethod
    def _finite_number(row: dict[str, Any], key: str) -> float | None:
        value = row.get(key)
        if isinstance(value, bool):
            return None
        try:
            number = float(value)
        except (TypeError, ValueError, OverflowError):
            return None
        return number if math.isfinite(number) else None

    @staticmethod
    def _positive_integer(row: dict[str, Any], key: str) -> int | None:
        value = row.get(key)
        if isinstance(value, bool):
            return None
        try:
            number = int(value)
        except (TypeError, ValueError, OverflowError):
            return None
        # Reject fractional numeric values rather than silently truncating them.
        try:
            if float(value) != number:
                return None
        except (TypeError, ValueError, OverflowError):
            return None
        return number if number > 0 else None

    def signals(self, min_confidence: float = 0.75) -> list[PaperLeadLagSignal]:
        try:
            min_confidence = float(min_confidence)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("min_confidence must be finite and between 0 and 1") from exc
        if not math.isfinite(min_confidence) or not 0.0 <= min_confidence <= 1.0:
            raise ValueError("min_confidence must be finite and between 0 and 1")

        result: list[PaperLeadLagSignal] = []
        for row in self.load():
            # Eligibility must be an explicit JSON boolean; truthy strings such as
            # "false" must never promote a malformed or untrusted learning record.
            if row.get("eligible") is not True:
                continue

            symbol = self._text(row, "symbol")
            leader = self._text(row, "leader")
            follower = self._text(row, "follower")
            direction = self._text(row, "direction")
            regime = self._text(row, "regime") or "UNKNOWN"
            horizon_ms = self._positive_integer(row, "horizon_ms")
            samples = self._positive_integer(row, "samples")
            expectancy_bps = self._finite_number(row, "expectancy_bps")
            confidence = self._finite_number(row, "confidence")

            if (
                not symbol or not leader or not follower or leader.casefold() == follower.casefold()
                or direction is None or direction.upper() not in {"UP", "DOWN"}
                or horizon_ms is None or samples is None
                or expectancy_bps is None or confidence is None
                or not 0.0 <= confidence <= 1.0
                or confidence < min_confidence
            ):
                continue

            result.append(PaperLeadLagSignal(
                symbol=symbol.upper(),
                leader=leader.lower(),
                follower=follower.lower(),
                direction=direction.upper(),
                horizon_ms=horizon_ms,
                expectancy_bps=expectancy_bps,
                confidence=confidence,
                samples=samples,
                regime=regime.upper(),
                paper_only=True,
            ))
        result.sort(key=lambda x: (x.expectancy_bps, x.confidence, x.samples), reverse=True)
        return result
