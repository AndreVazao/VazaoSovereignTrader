from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class SharedSourceTrustPolicy:
    """Local trust policy; remote artifacts cannot self-assign authority."""

    scores: dict[str, float]
    default_score: float = 0.0
    max_score: float = 0.90

    def score(self, source_node_ref: str) -> float:
        value = float(self.scores.get(str(source_node_ref), self.default_score))
        return max(0.0, min(self.max_score, value))


@dataclass(frozen=True)
class SharedAggregate:
    artifact_type: str
    strategy_id: str
    market: str
    regime: str
    horizon_seconds: int
    sample_count: int
    win_count: int
    win_rate: float
    mean_net_bps: float
    median_net_bps: float
    source_count: int
    aggregate_trust: float
    eligible: bool

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "artifact_type": self.artifact_type,
            "strategy_id": self.strategy_id,
            "market": self.market,
            "regime": self.regime,
            "horizon_seconds": self.horizon_seconds,
            "sample_count": self.sample_count,
            "win_count": self.win_count,
            "win_rate": self.win_rate,
            "mean_net_bps": self.mean_net_bps,
            "median_net_bps": self.median_net_bps,
            "source_count": self.source_count,
            "aggregate_trust": self.aggregate_trust,
            "eligible": self.eligible,
        }


class SharedIntelligenceAggregator:
    """Builds advisory evidence from independent trusted sources.

    Source-supplied trust_score/source_count are deliberately ignored. Trust is
    assigned locally and source diversity is derived from source_node_ref.
    Aggregates never authorize orders.
    """

    def __init__(
        self,
        policy: SharedSourceTrustPolicy,
        *,
        min_sources: int = 2,
        min_trust: float = 0.50,
    ):
        self.policy = policy
        self.min_sources = max(1, int(min_sources))
        self.min_trust = max(0.0, min(1.0, float(min_trust)))

    @staticmethod
    def _key(payload: dict[str, Any]) -> tuple[Any, ...]:
        return (
            str(payload.get("artifact_type", "")),
            str(payload.get("strategy_id", "")),
            str(payload.get("market", "")),
            str(payload.get("regime", "")),
            int(payload.get("horizon_seconds", 0)),
        )

    def aggregate(self, rows: Iterable[dict[str, Any]]) -> list[SharedAggregate]:
        groups: dict[tuple[Any, ...], dict[str, dict[str, Any]]] = {}
        for row in rows:
            payload = row.get("artifact", row) if isinstance(row, dict) else None
            if not isinstance(payload, dict) or not bool(payload.get("eligible", False)):
                continue
            node = str(payload.get("source_node_ref", "")).strip()
            if not node:
                continue
            trust = self.policy.score(node)
            if trust <= 0.0:
                continue
            key = self._key(payload)
            group = groups.setdefault(key, {})
            # One contribution per source node: prevents duplicate amplification.
            previous = group.get(node)
            if previous is None or int(payload.get("created_at_ms", 0)) > int(previous.get("created_at_ms", 0)):
                group[node] = dict(payload)

        result: list[SharedAggregate] = []
        for key, sources in groups.items():
            trusted = [(node, payload, self.policy.score(node)) for node, payload in sources.items()]
            if len(trusted) < self.min_sources:
                continue
            total_weight = sum(trust for _, _, trust in trusted)
            if total_weight <= 0:
                continue
            weighted_win_rate = sum(float(p["win_rate"]) * t for _, p, t in trusted) / total_weight
            weighted_mean = sum(float(p["mean_net_bps"]) * t for _, p, t in trusted) / total_weight
            weighted_median = sum(float(p["median_net_bps"]) * t for _, p, t in trusted) / total_weight
            sample_count = sum(int(p["sample_count"]) for _, p, _ in trusted)
            win_count = sum(int(p["win_count"]) for _, p, _ in trusted)
            empirical_rate = win_count / sample_count if sample_count else 0.0
            aggregate_trust = 1.0
            for _, _, trust in trusted:
                aggregate_trust *= 1.0 - trust
            aggregate_trust = 1.0 - aggregate_trust
            eligible = aggregate_trust >= self.min_trust and sample_count > 0
            result.append(
                SharedAggregate(
                    artifact_type=key[0], strategy_id=key[1], market=key[2], regime=key[3],
                    horizon_seconds=key[4], sample_count=sample_count, win_count=win_count,
                    win_rate=min(1.0, max(0.0, (weighted_win_rate + empirical_rate) / 2.0)),
                    mean_net_bps=weighted_mean, median_net_bps=weighted_median,
                    source_count=len(trusted), aggregate_trust=aggregate_trust, eligible=eligible,
                )
            )
        return result
