from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from PC_ENGINE.radar.evidence_stress import EvidenceStatisticalStressTester


@dataclass(frozen=True)
class CandidateSpec:
    """Immutable identity for a PAPER strategy/evidence candidate."""

    candidate_id: str
    version: str
    strategy: str
    configuration: tuple[tuple[str, str], ...] = ()
    evidence_type: str = ""
    evidence_name: str = ""
    symbol: str = ""
    regime: str = ""
    horizon_ms: int = 0

    def __post_init__(self) -> None:
        if not self.candidate_id.strip():
            raise ValueError("candidate_id must not be empty")
        if not self.version.strip():
            raise ValueError("version must not be empty")
        if not self.strategy.strip():
            raise ValueError("strategy must not be empty")


@dataclass(frozen=True)
class CandidateObservation:
    candidate_id: str
    version: str
    symbol: str
    timestamp_ms: int
    action: str
    net_bps: float
    risk_authorized: bool
    risk_violation: bool = False
    latency_ms: float = 0.0
    slippage_bps: float = 0.0


@dataclass(frozen=True)
class CandidateMetrics:
    candidate_id: str
    version: str
    samples: int
    wins: int
    win_rate: float
    mean_net_bps: float
    median_net_bps: float
    max_drawdown_bps: float
    mean_latency_ms: float
    mean_slippage_bps: float
    risk_violations: int
    validated: bool


@dataclass(frozen=True)
class PromotionDecision:
    candidate_id: str
    version: str
    eligible: bool
    reason: str
    metrics: CandidateMetrics


@dataclass
class ChampionChallengerBook:
    """PAPER-only registry and audit ledger.

    A champion is a reference slot, not an automatic trading privilege.
    Challengers are evaluated on the same observations/cost assumptions.
    No method here authorizes REAL execution or changes the Risk Engine.
    """

    champion: CandidateSpec | None = None
    candidates: dict[str, CandidateSpec] = field(default_factory=dict)
    observations: list[CandidateObservation] = field(default_factory=list)
    audit: list[PromotionDecision] = field(default_factory=list)

    def register(self, candidate: CandidateSpec) -> None:
        existing = self.candidates.get(candidate.candidate_id)
        if existing is not None and existing.version != candidate.version:
            raise ValueError("candidate_id already exists with a different version")
        self.candidates[candidate.candidate_id] = candidate

    def set_champion(self, candidate_id: str) -> None:
        candidate = self.candidates.get(candidate_id)
        if candidate is None:
            raise KeyError(f"unknown candidate: {candidate_id}")
        self.champion = candidate

    def record(self, observation: CandidateObservation) -> None:
        candidate = self.candidates.get(observation.candidate_id)
        if candidate is None:
            raise KeyError(f"unknown candidate: {observation.candidate_id}")
        if observation.version != candidate.version:
            raise ValueError("observation version does not match candidate")
        if observation.timestamp_ms <= 0:
            raise ValueError("timestamp_ms must be positive")
        if observation.action.upper() not in {"BUY", "SELL", "HOLD"}:
            raise ValueError("action must be BUY, SELL or HOLD")
        if observation.risk_violation and observation.risk_authorized:
            raise ValueError("risk violation cannot be risk-authorized")
        if observation.latency_ms < 0 or observation.slippage_bps < 0:
            raise ValueError("latency/slippage cannot be negative")
        self.observations.append(observation)

    @staticmethod
    def _metrics(
        candidate: CandidateSpec,
        observations: Iterable[CandidateObservation],
        *,
        min_samples: int,
        min_mean_net_bps: float,
        max_drawdown_bps: float,
        max_risk_violations: int,
    ) -> CandidateMetrics:
        rows = sorted(observations, key=lambda item: item.timestamp_ms)
        values = [float(item.net_bps) for item in rows]
        samples = len(values)
        wins = sum(value > 0 for value in values)
        mean = sum(values) / samples if samples else 0.0
        ordered = sorted(values)
        if samples:
            mid = samples // 2
            median = ordered[mid] if samples % 2 else (ordered[mid - 1] + ordered[mid]) / 2.0
        else:
            median = 0.0
        equity = peak = 0.0
        drawdown = 0.0
        for value in values:
            equity += value
            peak = max(peak, equity)
            drawdown = max(drawdown, peak - equity)
        risk_violations = sum(1 for item in rows if item.risk_violation)
        mean_latency = sum(item.latency_ms for item in rows) / samples if samples else 0.0
        mean_slippage = sum(item.slippage_bps for item in rows) / samples if samples else 0.0
        validated = (
            samples >= max(1, int(min_samples))
            and mean > float(min_mean_net_bps)
            and drawdown <= max(0.0, float(max_drawdown_bps))
            and risk_violations <= max(0, int(max_risk_violations))
        )
        return CandidateMetrics(
            candidate_id=candidate.candidate_id,
            version=candidate.version,
            samples=samples,
            wins=wins,
            win_rate=round(wins / samples, 6) if samples else 0.0,
            mean_net_bps=round(mean, 6),
            median_net_bps=round(median, 6),
            max_drawdown_bps=round(drawdown, 6),
            mean_latency_ms=round(mean_latency, 6),
            mean_slippage_bps=round(mean_slippage, 6),
            risk_violations=risk_violations,
            validated=validated,
        )

    def evaluate(
        self,
        *,
        min_samples: int = 30,
        min_mean_net_bps: float = 0.0,
        max_drawdown_bps: float = 100.0,
        max_risk_violations: int = 0,
    ) -> list[CandidateMetrics]:
        return [
            self._metrics(
                candidate,
                (row for row in self.observations if row.candidate_id == candidate.candidate_id),
                min_samples=min_samples,
                min_mean_net_bps=min_mean_net_bps,
                max_drawdown_bps=max_drawdown_bps,
                max_risk_violations=max_risk_violations,
            )
            for candidate in self.candidates.values()
        ]

    def assess_with_evidence(
        self,
        candidate_id: str,
        states: list[dict],
        *,
        costs_bps: tuple[float, ...] = (28.0, 35.0, 42.0, 56.0),
        min_cost_scenarios: int = 3,
        validator_kwargs: dict | None = None,
        train_size: int = 200,
        test_size: int = 100,
        step_size: int | None = None,
        horizons_ms: tuple[int, ...] = (1000, 5000, 15000, 60000, 300000),
        min_samples: int = 30,
        min_mean_net_bps: float = 0.0,
        max_drawdown_bps: float = 100.0,
        max_risk_violations: int = 0,
    ) -> PromotionDecision:
        """Assess a challenger through chronological OOS and cost-stress gates.

        PAPER research only. This never promotes or authorizes execution.
        """
        candidate = self.candidates.get(candidate_id)
        if candidate is None:
            raise KeyError(f"unknown candidate: {candidate_id}")
        metrics = self._metrics(
            candidate,
            (row for row in self.observations if row.candidate_id == candidate_id),
            min_samples=min_samples,
            min_mean_net_bps=min_mean_net_bps,
            max_drawdown_bps=max_drawdown_bps,
            max_risk_violations=max_risk_violations,
        )
        key = (
            candidate.evidence_type,
            candidate.evidence_name,
            candidate.symbol,
            candidate.regime,
            int(candidate.horizon_ms),
        )
        reasons: list[str] = []
        if not metrics.validated:
            reasons.append("base PAPER metrics gate failed")
        if not all(key):
            reasons.append("candidate evidence identity is incomplete")
        else:
            tester = EvidenceStatisticalStressTester(
                costs_bps=costs_bps,
                validator_kwargs=dict(validator_kwargs or {}),
            )
            stress = tester.validate(
                states,
                train_size=train_size,
                test_size=test_size,
                step_size=step_size,
                horizons_ms=horizons_ms,
            )
            matching = [row for row in stress if (
                row.evidence_type,
                row.evidence_name,
                row.symbol,
                row.regime,
                row.horizon_ms,
            ) == key]
            robust = tester.robustness(stress, min_cost_scenarios=min_cost_scenarios).get(key, False)
            if not matching or not robust:
                reasons.append("OOS cost-stress evidence gate failed")
            elif not all(row.validated for row in matching):
                reasons.append("one or more required cost scenarios failed validation")
        eligible = not reasons
        decision = PromotionDecision(
            candidate_id,
            candidate.version,
            eligible,
            "eligible for human-reviewed PAPER promotion" if eligible else "; ".join(reasons),
            metrics,
        )
        self.audit.append(decision)
        return decision

    def assess(
        self,
        candidate_id: str,
        *,
        min_samples: int = 30,
        min_mean_net_bps: float = 0.0,
        max_drawdown_bps: float = 100.0,
        max_risk_violations: int = 0,
        required_stress_scenarios: int = 0,
        validated_stress_scenarios: int = 0,
    ) -> PromotionDecision:
        candidate = self.candidates.get(candidate_id)
        if candidate is None:
            raise KeyError(f"unknown candidate: {candidate_id}")
        metrics = self._metrics(
            candidate,
            (row for row in self.observations if row.candidate_id == candidate_id),
            min_samples=min_samples,
            min_mean_net_bps=min_mean_net_bps,
            max_drawdown_bps=max_drawdown_bps,
            max_risk_violations=max_risk_violations,
        )
        reasons: list[str] = []
        if not metrics.validated:
            reasons.append("base PAPER metrics gate failed")
        if required_stress_scenarios > validated_stress_scenarios:
            reasons.append("cost-stress gate failed")
        if reasons:
            decision = PromotionDecision(candidate_id, candidate.version, False, "; ".join(reasons), metrics)
        else:
            decision = PromotionDecision(
                candidate_id,
                candidate.version,
                True,
                "eligible for human-reviewed PAPER promotion",
                metrics,
            )
        self.audit.append(decision)
        return decision
