from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

from PC_ENGINE.learning.state_signature import SignatureStat, StateSignature, StateSignatureLearningEngine
from PC_ENGINE.learning.learning_consensus import PaperLearningConsensus


@dataclass(frozen=True)
class OpportunityScore:
    symbol: str
    score: float
    confidence: float
    action: str
    strategy_score: float
    learning_bonus: float
    cost_penalty: float
    freshness: float
    reason: str
    consensus_bonus: float = 0.0
    consensus: bool = False
    latency_bonus: float = 0.0
    latency_edge_bps: float = 0.0
    latency_freshness: float = 0.0
    external_latency_bonus: float = 0.0
    external_latency_edge_bps: float = 0.0
    external_latency_freshness: float = 0.0


class PaperOpportunityEngine:
    """Ranks PAPER opportunities without authorizing orders.

    Learning is deliberately advisory: it can increase/decrease an opportunity
    score, but RiskEngine remains the final authority before execution.
    """

    def __init__(self, settings: dict | None = None) -> None:
        settings = settings or {}
        self.enabled = bool(settings.get("enabled", True))
        self.learning_weight = max(0.0, float(settings.get("learning_weight", 0.25)))
        self.cost_weight = max(0.0, float(settings.get("cost_weight", 0.15)))
        self.stale_after_seconds = max(1.0, float(settings.get("stale_after_seconds", 120.0)))
        self.horizon_ms = max(1000, int(settings.get("horizon_ms", 5000)))
        self.learning_path = Path(
            settings.get(
                "learning_path",
                "PC_ENGINE/data/radar/state_signature_learning.jsonl",
            )
        )
        self._stats_mtime = 0.0
        self._stats: list[SignatureStat] = []
        self.consensus = PaperLearningConsensus(settings)
        self.latency_weight = max(0.0, float(settings.get("latency_weight", 0.15)))
        self.latency_max_bonus = max(0.0, min(0.30, float(settings.get("latency_max_bonus", 0.15))))
        self.latency_stale_after_ms = max(100, int(settings.get("latency_stale_after_ms", 1000)))
        self.latency_min_edge_bps = max(0.1, float(settings.get("latency_min_edge_bps", 1.0)))
        self.latency_path = Path(settings.get("latency_path", "PC_ENGINE/data/radar/websocket_latency_edges.jsonl"))
        self.external_latency_weight = max(0.0, float(settings.get("external_latency_weight", 0.10)))
        self.external_latency_max_bonus = max(0.0, min(0.20, float(settings.get("external_latency_max_bonus", 0.10))))
        self.external_latency_stale_after_ms = max(100, int(settings.get("external_latency_stale_after_ms", 2000)))
        self.external_latency_min_edge_bps = max(0.1, float(settings.get("external_latency_min_edge_bps", 1.0)))
        self.external_latency_path = Path(settings.get("external_latency_profile_path", "PC_ENGINE/data/radar/external_source_latency_profiles.jsonl"))

    def _load_stats(self) -> None:
        try:
            mtime = self.learning_path.stat().st_mtime
        except FileNotFoundError:
            self._stats = []
            self._stats_mtime = 0.0
            return
        if mtime <= self._stats_mtime:
            return
        rows: list[SignatureStat] = []
        try:
            with self.learning_path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    try:
                        raw = json.loads(line)
                        rows.append(SignatureStat(**raw))
                    except (TypeError, ValueError, json.JSONDecodeError):
                        continue
        except OSError:
            return
        self._stats = rows
        self._stats_mtime = mtime


    def _latest_latency_edge(self, symbol: str, now_ms: int, direction: str = "UP") -> dict | None:
        try:
            with self.latency_path.open("r", encoding="utf-8") as handle:
                handle.seek(0, 2)
                size = handle.tell()
                handle.seek(max(0, size - 131072))
                lines = handle.read().splitlines()
        except (FileNotFoundError, OSError):
            return None
        for line in reversed(lines):
            try:
                row = json.loads(line)
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
            if str(row.get("symbol", "")).upper() != symbol.upper():
                continue
            if str(row.get("direction", "")).upper() != direction.upper():
                continue
            if not bool(row.get("eligible", False)):
                continue
            observed_ts_ms = int(row.get("observed_ts_ms", 0) or 0)
            if not observed_ts_ms:
                continue
            age_ms = max(0, now_ms - observed_ts_ms)
            if age_ms > self.latency_stale_after_ms:
                return None
            row["_freshness"] = max(0.0, 1.0 - age_ms / self.latency_stale_after_ms)
            return row
        return None

    def _latest_external_latency_profile(self, symbol: str, now_ms: int, direction: str = "UP") -> dict | None:
        try:
            with self.external_latency_path.open("r", encoding="utf-8") as handle:
                handle.seek(0, 2)
                size = handle.tell()
                handle.seek(max(0, size - 131072))
                lines = handle.read().splitlines()
        except (FileNotFoundError, OSError):
            return None
        for line in reversed(lines):
            try:
                row = json.loads(line)
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
            if str(row.get("symbol", "")).upper() != symbol.upper():
                continue
            if str(row.get("direction", "")).upper() != direction.upper():
                continue
            if not bool(row.get("eligible", False)):
                continue
            observed_ts_ms = int(row.get("observed_ts_ms", 0) or 0)
            if not observed_ts_ms:
                continue
            age_ms = max(0, now_ms - observed_ts_ms)
            if age_ms > self.external_latency_stale_after_ms:
                return None
            row["_freshness"] = max(0.0, 1.0 - age_ms / self.external_latency_stale_after_ms)
            return row
        return None

    def score(
        self,
        *,
        symbol: str,
        strategy_score: float,
        action: str,
        spread_pct: float,
        state: dict | None,
        now_ms: int | None = None,
    ) -> OpportunityScore:
        normalized_action = str(action).upper()
        if not self.enabled or normalized_action not in {"BUY", "SELL"}:
            return OpportunityScore(
                symbol, 0.0, 0.0, action, max(0.0, min(1.0, strategy_score)),
                0.0, 0.0, 0.0, "sem oportunidade BUY/SELL",
            )

        now_ms = int(time.time() * 1000) if now_ms is None else int(now_ms)
        base = max(0.0, min(1.0, float(strategy_score)))
        cost_penalty = max(0.0, min(0.50, float(spread_pct) * self.cost_weight * 100.0))

        learning_bonus = 0.0
        consensus_bonus = 0.0
        latency_bonus = 0.0
        latency_edge_bps = 0.0
        latency_freshness = 0.0
        external_latency_bonus = 0.0
        external_latency_edge_bps = 0.0
        external_latency_freshness = 0.0
        consensus_ok = False
        learning_reason = "sem aprendizagem elegível"
        if state:
            timestamp_ms = int(state.get("timestamp_ms", 0))
            age_s = max(0.0, (now_ms - timestamp_ms) / 1000.0) if timestamp_ms else self.stale_after_seconds + 1
            freshness = max(0.0, min(1.0, 1.0 - age_s / self.stale_after_seconds))
            if freshness > 0.0:
                self._load_stats()
                learned = StateSignatureLearningEngine().rank(
                    state, self._stats, horizon_ms=self.horizon_ms
                )
                if learned is not None:
                    # Convert only a bounded amount of historical expectancy
                    # into score. This prevents old learning from dominating.
                    learning_bonus = max(-0.25, min(0.25, learned.lower_ci_bps / 100.0))
                    learning_bonus *= self.learning_weight * freshness
                    learning_reason = (
                        f"assinatura {learned.samples} amostras, "
                        f"CI95 inferior {learned.lower_ci_bps:.2f} bps"
                    )
                consensus = self.consensus.evaluate(state)
                consensus_bonus = consensus.bonus * freshness
                consensus_ok = consensus.agreement
                if consensus_ok:
                    learning_reason += "; " + consensus.reason
            else:
                freshness = 0.0
        else:
            freshness = 0.0

        direction = "UP" if normalized_action == "BUY" else "DOWN"
        latency_edge = self._latest_latency_edge(symbol, now_ms, direction)
        if latency_edge is not None:
            latency_edge_bps = max(0.0, float(latency_edge.get("net_expected_edge_bps", 0.0)))
            latency_freshness = float(latency_edge.get("_freshness", 0.0))
            edge_strength = max(0.0, min(1.0, latency_edge_bps / self.latency_min_edge_bps))
            persistence = max(0.0, min(1.0, float(latency_edge.get("persistence_ratio", 0.0))))
            same_direction = max(0.0, min(1.0, float(latency_edge.get("same_direction_ratio", 0.0))))
            latency_bonus = min(
                self.latency_max_bonus,
                self.latency_weight * edge_strength * persistence * same_direction * latency_freshness,
            )

        external_profile = self._latest_external_latency_profile(symbol, now_ms, direction)
        if external_profile is not None:
            external_latency_edge_bps = max(0.0, float(external_profile.get("net_edge_bps", 0.0)))
            external_latency_freshness = float(external_profile.get("_freshness", 0.0))
            edge_strength = max(0.0, min(1.0, external_latency_edge_bps / self.external_latency_min_edge_bps))
            same_direction = max(0.0, min(1.0, float(external_profile.get("same_direction_ratio", 0.0))))
            external_latency_bonus = min(
                self.external_latency_max_bonus,
                self.external_latency_weight * edge_strength * same_direction * external_latency_freshness,
            )

        final = max(0.0, min(1.0, base + learning_bonus + consensus_bonus + latency_bonus + external_latency_bonus - cost_penalty))
        confidence = max(0.0, min(1.0, 0.65 * base + 0.35 * (1.0 if learning_bonus > 0 else 0.0)))
        reason = f"estratégia={base:.3f}; {learning_reason}; latency={latency_edge_bps:.2f}bps/{latency_freshness:.2f}; external={external_latency_edge_bps:.2f}bps/{external_latency_freshness:.2f}; custo/spread={cost_penalty:.3f}"
        return OpportunityScore(
            symbol=symbol,
            score=round(final, 6),
            confidence=round(confidence, 6),
            action=normalized_action,
            strategy_score=round(base, 6),
            learning_bonus=round(learning_bonus, 6),
            cost_penalty=round(cost_penalty, 6),
            freshness=round(freshness, 6),
            reason=reason,
            consensus_bonus=round(consensus_bonus, 6),
            consensus=consensus_ok,
            latency_bonus=round(latency_bonus, 6),
            latency_edge_bps=round(latency_edge_bps, 4),
            latency_freshness=round(latency_freshness, 6),
            external_latency_bonus=round(external_latency_bonus, 6),
            external_latency_edge_bps=round(external_latency_edge_bps, 4),
            external_latency_freshness=round(external_latency_freshness, 6),
        )
