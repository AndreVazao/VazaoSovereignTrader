from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Iterable

from PC_ENGINE.radar.champion_challenger import CandidateSpec


class PaperChampionRuntime:
    """PAPER-only shadow runner with durable chronological outcome attribution."""

    def __init__(
        self,
        candidates: Iterable[CandidateSpec] = (),
        *,
        path: str | Path = "PC_ENGINE/data/radar/champion_challenger_states.jsonl",
        outcome_path: str | Path | None = None,
        pending_path: str | Path | None = None,
    ) -> None:
        self.path = Path(path)
        self.outcome_path = Path(outcome_path) if outcome_path else self.path.with_name(
            "champion_challenger_outcomes.jsonl"
        )
        self.pending_path = Path(pending_path) if pending_path else self.path.with_name(
            "champion_challenger_pending.jsonl"
        )
        self.candidates: dict[str, CandidateSpec] = {}
        self.cycles = 0
        self.records = 0
        self.outcomes = 0
        self._pending: list[dict] = self._load_pending()
        for candidate in candidates:
            self.register(candidate)

    def register(self, candidate: CandidateSpec) -> None:
        existing = self.candidates.get(candidate.candidate_id)
        if existing is not None and existing.version != candidate.version:
            raise ValueError("candidate_id already exists with a different version")
        self.candidates[candidate.candidate_id] = candidate

    def _load_pending(self) -> list[dict]:
        if not self.pending_path.exists():
            return []
        rows: list[dict] = []
        for line in self.pending_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            required = {
                "candidate_id", "version", "strategy", "symbol", "regime",
                "entry_timestamp_ms", "target_timestamp_ms", "horizon_ms",
                "action", "entry_price", "cost_bps", "shared_risk_authorized",
            }
            if not required.issubset(row):
                raise ValueError("pending outcome record is incomplete")
            if row["action"] not in {"BUY", "SELL"}:
                raise ValueError("pending outcome action is invalid")
            if not math.isfinite(float(row["entry_price"])) or float(row["entry_price"]) <= 0:
                raise ValueError("pending outcome entry price is invalid")
            if not math.isfinite(float(row["cost_bps"])) or float(row["cost_bps"]) < 0:
                raise ValueError("pending outcome cost is invalid")
            rows.append(row)
        return rows

    def _persist_pending(self) -> None:
        self.pending_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.pending_path.with_suffix(self.pending_path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as handle:
            for row in self._pending:
                handle.write(json.dumps(row, separators=(",", ":"), sort_keys=True) + "\n")
        tmp.replace(self.pending_path)

    @staticmethod
    def _cost_bps(cost_context: dict | None) -> float:
        context = cost_context or {}
        total = 0.0
        for key in ("fee_bps", "spread_bps", "slippage_bps", "latency_bps"):
            value = float(context.get(key, 0.0))
            if not math.isfinite(value) or value < 0:
                raise ValueError("cost context must contain finite non-negative bps")
            total += value
        return total

    def _resolve(self, symbol: str, timestamp_ms: int, price: float) -> int:
        resolved = 0
        remaining: list[dict] = []
        for row in self._pending:
            if row["symbol"] != symbol or timestamp_ms < row["target_timestamp_ms"]:
                remaining.append(row)
                continue
            direction = 1.0 if row["action"] == "BUY" else -1.0
            gross_bps = ((price - row["entry_price"]) / row["entry_price"]) * 10000.0 * direction
            net_bps = gross_bps - row["cost_bps"]
            outcome = {
                "candidate_id": row["candidate_id"],
                "version": row["version"],
                "strategy": row["strategy"],
                "symbol": row["symbol"],
                "regime": row["regime"],
                "entry_timestamp_ms": row["entry_timestamp_ms"],
                "exit_timestamp_ms": timestamp_ms,
                "horizon_ms": row["horizon_ms"],
                "action": row["action"],
                "entry_price": row["entry_price"],
                "exit_price": price,
                "gross_bps": round(gross_bps, 8),
                "cost_bps": round(row["cost_bps"], 8),
                "net_bps": round(net_bps, 8),
                "risk_authorized": row["shared_risk_authorized"],
                "paper_only": True,
            }
            self.outcome_path.parent.mkdir(parents=True, exist_ok=True)
            with self.outcome_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(outcome, separators=(",", ":"), sort_keys=True) + "\n")
            self.outcomes += 1
            resolved += 1
        self._pending = remaining
        self._persist_pending()
        return resolved

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

        candidate_cost = self._cost_bps(cost_context)
        self._resolve(symbol, timestamp_ms, price)
        evidence = state.get("strategy_evidence") or {}
        regime = str(state.get("regime", ""))
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
                    "regime": regime,
                    "action": action,
                    "score": round(score, 8),
                    "confidence": round(max(0.0, min(1.0, confidence)), 8),
                    "cost_context": dict(cost_context or {}),
                    "shared_risk_authorized": bool(shared_risk_authorized),
                    "paper_only": True,
                }
            )
            if action in {"BUY", "SELL"} and candidate.horizon_ms > 0:
                self._pending.append(
                    {
                        "candidate_id": candidate.candidate_id,
                        "version": candidate.version,
                        "strategy": candidate.strategy,
                        "symbol": symbol,
                        "regime": regime,
                        "entry_timestamp_ms": timestamp_ms,
                        "target_timestamp_ms": timestamp_ms + candidate.horizon_ms,
                        "horizon_ms": candidate.horizon_ms,
                        "action": action,
                        "entry_price": price,
                        "cost_bps": candidate_cost,
                        "shared_risk_authorized": bool(shared_risk_authorized),
                    }
                )

        self._persist_pending()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, separators=(",", ":"), sort_keys=True) + "\n")
        self.cycles += 1
        self.records += len(rows)
        return len(rows)

    def flush(self) -> int:
        """Discard unresolved observations without inventing future prices."""
        count = len(self._pending)
        self._pending.clear()
        self._persist_pending()
        return count

    def snapshot(self) -> dict:
        return {
            "enabled": bool(self.candidates),
            "candidate_count": len(self.candidates),
            "candidate_ids": sorted(self.candidates),
            "cycles": self.cycles,
            "records": self.records,
            "outcomes": self.outcomes,
            "pending": len(self._pending),
            "path": str(self.path),
            "outcome_path": str(self.outcome_path),
            "pending_path": str(self.pending_path),
            "paper_only": True,
        }