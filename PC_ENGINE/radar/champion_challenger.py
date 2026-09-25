from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from PC_ENGINE.radar.evidence_stress import EvidenceStatisticalStressTester
from PC_ENGINE.radar.champion_outcomes import ChampionOutcomeAggregator, ChampionOutcomeMetrics, ChampionOutcomeStressStat
from PC_ENGINE.radar.evidence_ledger import EvidenceLedger, EvidenceLedgerRecord, EvidencePlaneSummary


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

        if evidence_ledger_path is not None:
            durable_rows = [row for row in outcome_stress if (
                row.candidate_id == candidate.candidate_id
                and row.version == candidate.version
                and row.symbol == candidate.symbol
                and row.regime == candidate.regime
                and row.horizon_ms == candidate.horizon_ms
            )]
            durable_summary = EvidencePlaneSummary(
                name="durable_outcome",
                status="PASS" if outcome_decision.eligible else "FAIL",
                samples=outcome_metrics.samples if outcome_metrics else 0,
                scenarios=len(durable_rows),
                validated_scenarios=sum(row.validated for row in durable_rows),
                mean_net_bps=outcome_metrics.mean_net_bps if outcome_metrics else 0.0,
                lower_ci_bps=outcome_metrics.lower_ci_bps if outcome_metrics else 0.0,
                bootstrap_lower_ci_bps=outcome_metrics.bootstrap_lower_ci_bps if outcome_metrics else 0.0,
                positive_fold_ratio=outcome_metrics.positive_fold_ratio if outcome_metrics else 0.0,
                folds=outcome_metrics.folds if outcome_metrics else 0,
            )

            oos_tester = EvidenceStatisticalStressTester(
                costs_bps=costs_bps,
                validator_kwargs=dict(validator_kwargs or {}),
            )
            oos_stress = oos_tester.validate(
                states,
                train_size=train_size,
                test_size=test_size,
                step_size=step_size,
                horizons_ms=horizons_ms,
            )
            oos_key = (
                candidate.evidence_type,
                candidate.evidence_name,
                candidate.symbol,
                candidate.regime,
                candidate.horizon_ms,
            )
            oos_rows = [row for row in oos_stress if (
                row.evidence_type, row.evidence_name, row.symbol,
                row.regime, row.horizon_ms,
            ) == oos_key]
            base_oos = oos_rows[0] if oos_rows else None
            oos_summary = EvidencePlaneSummary(
                name="chronological_oos",
                status="PASS" if oos_decision.eligible else "FAIL",
                samples=base_oos.samples if base_oos else 0,
                scenarios=len(oos_rows),
                validated_scenarios=sum(row.validated for row in oos_rows),
                mean_net_bps=base_oos.mean_net_bps if base_oos else 0.0,
                lower_ci_bps=0.0,
                bootstrap_lower_ci_bps=base_oos.bootstrap_lower_ci_bps if base_oos else 0.0,
                positive_fold_ratio=base_oos.positive_fold_ratio if base_oos else 0.0,
                folds=0,
            )
            timestamps = [
                int(state.get("timestamp_ms", 0) or 0)
                for state in states
                if int(state.get("timestamp_ms", 0) or 0) > 0
            ]
            outcome_timestamps = [
                int(row[key])
                for row in outcome_rows
                if row.get("candidate_id") == candidate.candidate_id
                and row.get("version") == candidate.version
                for key in ("entry_timestamp_ms", "exit_timestamp_ms")
                if int(row.get(key, 0) or 0) > 0
            ]
            all_timestamps = timestamps + outcome_timestamps
            data_start_ms = min(all_timestamps) if all_timestamps else 1
            data_end_ms = max(all_timestamps) if all_timestamps else data_start_ms
            EvidenceLedger.append(
                evidence_ledger_path,
                EvidenceLedgerRecord(
                    created_at_ms=data_end_ms,
                    candidate_id=candidate.candidate_id,
                    version=candidate.version,
                    strategy=candidate.strategy,
                    symbol=candidate.symbol,
                    regime=candidate.regime,
                    horizon_ms=candidate.horizon_ms,
                    eligible=decision.eligible,
                    reason=decision.reason,
                    reason_codes=EvidenceLedger.reason_codes(decision.reason),
                    data_start_ms=data_start_ms,
                    data_end_ms=data_end_ms,
                    state_count=len(states),
                    outcome_count=len(outcome_rows),
                    durable_outcome=durable_summary,
                    chronological_oos=oos_summary,
                    source_digest="0" * 64,
                ),
            )
        return decision


    def assess_outcomes(
        self,
        candidate_id: str,
        outcome_rows: list[dict],
        *,
        costs_bps: tuple[float, ...] = (28.0, 35.0, 42.0, 56.0),
        min_cost_scenarios: int = 3,
        min_samples: int = 30,
        min_folds: int = 2,
        min_mean_net_bps: float = 0.0,
        min_lower_ci_bps: float = 0.0,
        min_positive_fold_ratio: float = 0.50,
        fold_duration_ms: int = 300_000,
    ) -> tuple[PromotionDecision, ChampionOutcomeMetrics | None, list[ChampionOutcomeStressStat]]:
        """Gate a candidate using durable PAPER outcomes only."""
        candidate = self.candidates.get(candidate_id)
        if candidate is None:
            raise KeyError(f"unknown candidate: {candidate_id}")
        aggregator = ChampionOutcomeAggregator(
            min_samples=min_samples,
            min_folds=min_folds,
            min_mean_net_bps=min_mean_net_bps,
            min_lower_ci_bps=min_lower_ci_bps,
            min_positive_fold_ratio=min_positive_fold_ratio,
            fold_duration_ms=fold_duration_ms,
        )
        matching = [
            row for row in outcome_rows
            if row.get("candidate_id") == candidate.candidate_id
            and row.get("version") == candidate.version
        ]
        metrics_rows = aggregator.aggregate(matching, risk_authorized_only=True)
        metrics = next(
            (
                row for row in metrics_rows
                if row.symbol == candidate.symbol
                and row.regime == candidate.regime
                and row.horizon_ms == candidate.horizon_ms
            ),
            None,
        )
        stress = aggregator.stress(
            matching, costs_bps=costs_bps, risk_authorized_only=True
        )
        key = (
            candidate.candidate_id,
            candidate.version,
            candidate.strategy,
            candidate.symbol,
            candidate.regime,
            candidate.horizon_ms,
        )
        robust = aggregator.robustness(
            stress, min_cost_scenarios=min_cost_scenarios
        ).get(key, False)
        reasons = []
        if metrics is None or not metrics.validated:
            reasons.append("durable PAPER outcome gate failed")
        if not robust:
            reasons.append("durable PAPER cost-stress gate failed")
        eligible = not reasons
        decision = PromotionDecision(
            candidate.candidate_id,
            candidate.version,
            eligible,
            "eligible for human-reviewed PAPER promotion"
            if eligible
            else "; ".join(reasons),
            self._metrics(
                candidate,
                (row for row in self.observations if row.candidate_id == candidate.candidate_id),
                min_samples=1,
                min_mean_net_bps=-float("inf"),
                max_drawdown_bps=float("inf"),
                max_risk_violations=10**9,
            ),
        )
        self.audit.append(decision)
        return decision, metrics, stress

    def assess_unified_evidence(
        self,
        candidate_id: str,
        states: list[dict],
        outcome_rows: list[dict],
        *,
        costs_bps: tuple[float, ...] = (28.0, 35.0, 42.0, 56.0),
        min_cost_scenarios: int = 3,
        validator_kwargs: dict | None = None,
        train_size: int = 200,
        test_size: int = 100,
        step_size: int | None = None,
        horizons_ms: tuple[int, ...] = (1000, 5000, 15000, 60000, 300000),
        min_samples: int = 30,
        min_folds: int = 2,
        min_mean_net_bps: float = 0.0,
        min_lower_ci_bps: float = 0.0,
        min_positive_fold_ratio: float = 0.50,
        fold_duration_ms: int = 300_000,
        evidence_ledger_path: str | None = None,
    ) -> PromotionDecision:
        """Single PAPER evidence gate combining durable outcomes and OOS stress.

        The candidate must pass both independent evidence planes. Identity is
        exact (candidate/version/evidence identity), outcomes are restricted to
        Risk-authorized PAPER rows, and all requested cost scenarios must pass.
        This method only records an audit decision; it never changes champion
        state and never authorizes execution.
        """
        candidate = self.candidates.get(candidate_id)
        if candidate is None:
            raise KeyError(f"unknown candidate: {candidate_id}")

        reasons: list[str] = []
        audit_len = len(self.audit)

        outcome_decision, outcome_metrics, outcome_stress = self.assess_outcomes(
            candidate_id,
            outcome_rows,
            costs_bps=costs_bps,
            min_cost_scenarios=min_cost_scenarios,
            min_samples=min_samples,
            min_folds=min_folds,
            min_mean_net_bps=min_mean_net_bps,
            min_lower_ci_bps=min_lower_ci_bps,
            min_positive_fold_ratio=min_positive_fold_ratio,
            fold_duration_ms=fold_duration_ms,
        )
        if not outcome_decision.eligible:
            reasons.append(f"durable outcome gate failed: {outcome_decision.reason}")

        oos_decision = self.assess_with_evidence(
            candidate_id,
            states,
            costs_bps=costs_bps,
            min_cost_scenarios=min_cost_scenarios,
            validator_kwargs=validator_kwargs,
            train_size=train_size,
            test_size=test_size,
            step_size=step_size,
            horizons_ms=horizons_ms,
            min_samples=1,
            min_mean_net_bps=-float("inf"),
            max_drawdown_bps=float("inf"),
            max_risk_violations=10**9,
        )
        if not oos_decision.eligible:
            reasons.append(f"chronological OOS gate failed: {oos_decision.reason}")

        # The two component assessments are evidence calculations, not separate
        # audit events. Replace them with this single combined decision.
        del self.audit[audit_len:]

        metrics = self._metrics(
            candidate,
            (
                row for row in self.observations
                if row.candidate_id == candidate_id
                and row.version == candidate.version
                and row.risk_authorized
                and not row.risk_violation
            ),
            min_samples=1,
            min_mean_net_bps=-float("inf"),
            max_drawdown_bps=float("inf"),
            max_risk_violations=10**9,
        )
        if outcome_metrics is None:
            reasons.append("no matching Risk-authorized durable outcome metrics")
        if len(outcome_stress) < max(1, int(min_cost_scenarios)):
            reasons.append("durable outcome stress scenarios are incomplete")

        eligible = not reasons
        decision = PromotionDecision(
            candidate_id=candidate.candidate_id,
            version=candidate.version,
            eligible=eligible,
            reason=(
                "eligible for human-reviewed PAPER promotion"
                if eligible else "; ".join(reasons)
            ),
            metrics=metrics,
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
