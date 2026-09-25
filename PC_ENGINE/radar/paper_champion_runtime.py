from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Iterable

from PC_ENGINE.radar.champion_challenger import CandidateSpec


class PaperChampionRuntime:
    """PAPER-only shadow runner for champion/challenger state parity.

    Every registered candidate receives the same normalized market state and
    cost context. This layer never submits orders, never promotes a candidate,
    and never changes Risk Engine authorization.
    """

    def __init__(
        self,
        candidates: Iterable[CandidateSpec] = (),
        *,
        path: str | Path = "PC_ENGINE/data/radar/champion_challenger_states.jsonl",
    ) -> None:
        self.path = Path(path)
        self.candidates: dict[str, CandidateSpec] = {}
        self.cycles = 0
        self.records = 0
        for candidate in candidates:
            self.register(candidate)

    def register(self, candidate: CandidateSpec) -> None:
        existing = self.candidates.get(candidate.candidate_id)
        if existing is not None and existing.version != candidate.version:
            raise ValueError("candidate_id already exists with a different version")
        self.candidates[candidate.candidate_id] = candidate

    def observe(
        self,
        state: dict,
        *,
        cost_context: dict | None = None,
        shared_risk_authorized: bool = False,
    ) -> int:
        if not self.candidates:
            return 0
        symbol = str(state.get("symbol", "")).strip()
        timestamp_ms = int(state.get("timestamp_ms", 0))
        price = float(state.get("price", 0.0))
        if not symbol or timestamp_ms <= 0 or not math.isfinite(price) or price <= 0:
            raise ValueError("invalid market state for champion/challenger observation")

        evidence = state.get("strategy_evidence") or {}
        rows = []
        for candidate in self.candidates.values():
            record = evidence.get(candidate.strategy, {})
            action = str(record.get("action", state.get("action", "HOLD"))).upper()
            if action not in {"BUY", "SELL", "HOLD"}:
                action = "HOLD"
            score = float(record.get("score", 0.0))
            confidence = float(record.get("confidence", 0.0))
            if not math.isfinite(score) or not math.isfinite(confidence):
                raise ValueError("candidate evidence must be finite")
            rows.append(
                {
                    "candidate_id": candidate.candidate_id,
                    "version": candidate.version,
                    "strategy": candidate.strategy,
                    "symbol": symbol,
                    "timestamp_ms": timestamp_ms,
                    "price": price,
                    "regime": str(state.get("regime", "")),
                    "action": action,
                    "score": round(score, 8),
                    "confidence": round(max(0.0, min(1.0, confidence)), 8),
                    "cost_context": dict(cost_context or {}),
                    "shared_risk_authorized": bool(shared_risk_authorized),
                    "paper_only": True,
                }
            )

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, separators=(",", ":"), sort_keys=True) + "\n")
        self.cycles += 1
        self.records += len(rows)
        return len(rows)

    def snapshot(self) -> dict:
        return {
            "enabled": bool(self.candidates),
            "candidate_count": len(self.candidates),
            "candidate_ids": sorted(self.candidates),
            "cycles": self.cycles,
            "records": self.records,
            "path": str(self.path),
            "paper_only": True,
        }
