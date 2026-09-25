from __future__ import annotations

from dataclasses import dataclass
from PC_ENGINE.radar.evidence_statistics import bootstrap_lower_ci, summary

from PC_ENGINE.radar.evidence_outcomes import (
    EvidenceObservation,
    EvidenceOutcomeEngine,
    EvidenceOutcomeStat,
)


@dataclass(frozen=True)
class EvidenceOOSFold:
    fold: int
    train_start_ms: int
    train_end_ms: int
    test_start_ms: int
    test_end_ms: int
    train_eligible_groups: int
    oos_groups: int


@dataclass(frozen=True)
class EvidenceOOSStat:
    evidence_type: str
    evidence_name: str
    symbol: str
    regime: str
    horizon_ms: int
    folds: int
    train_eligible_folds: int
    samples: int
    wins: int
    win_rate: float
    mean_net_bps: float
    median_net_bps: float
    lower_ci_bps: float
    bootstrap_lower_ci_bps: float
    positive_fold_ratio: float
    validated: bool


class EvidenceWalkForwardValidator:
    """Chronological OOS validator for PAPER evidence.

    Training eligibility is learned only from observations whose outcomes
    finish before the next OOS window. OOS observations must also finish
    inside their own validation window. This prevents future-label leakage
    across fold boundaries.
    """

    def __init__(
        self,
        *,
        cost_bps: float = 28.0,
        min_train_samples: int = 30,
        min_train_mean_net_bps: float = 0.0,
        min_train_win_rate: float = 0.50,
        min_oos_samples: int = 20,
        min_oos_folds: int = 2,
        min_oos_mean_net_bps: float = 0.0,
        min_oos_win_rate: float = 0.50,
        min_oos_lower_ci_bps: float = 0.0,
    ) -> None:
        self.engine = EvidenceOutcomeEngine(
            cost_bps=cost_bps,
            min_samples=min_train_samples,
            min_mean_net_bps=min_train_mean_net_bps,
            min_win_rate=min_train_win_rate,
        )
        self.min_oos_samples = max(1, int(min_oos_samples))
        self.min_oos_folds = max(1, int(min_oos_folds))
        self.min_oos_mean_net_bps = float(min_oos_mean_net_bps)
        self.min_oos_win_rate = float(min_oos_win_rate)
        self.min_oos_lower_ci_bps = float(min_oos_lower_ci_bps)

    @staticmethod
    def _key(item: EvidenceObservation) -> tuple[str, str, str, str, int]:
        return (
            item.evidence_type,
            item.evidence_name,
            item.symbol,
            item.regime,
            item.horizon_ms,
        )

    @staticmethod
    def _stat_rows(observations: list[EvidenceObservation]) -> list[EvidenceOutcomeStat]:
        return [
            EvidenceOutcomeStat(
                evidence_type=item.evidence_type,
                evidence_name=item.evidence_name,
                symbol=item.symbol,
                regime=item.regime,
                horizon_ms=item.horizon_ms,
                samples=1,
                wins=int(item.net_bps > 0),
                win_rate=float(item.net_bps > 0),
                mean_net_bps=item.net_bps,
                median_net_bps=item.net_bps,
                lower_ci_bps=item.net_bps,
                eligible=False,
            )
            for item in observations
        ]

    def validate(
        self,
        states: list[dict],
        *,
        train_size: int = 200,
        test_size: int = 100,
        step_size: int | None = None,
        horizons_ms: tuple[int, ...] = (1000, 5000, 15000, 60000, 300000),
    ) -> tuple[list[EvidenceOOSFold], list[EvidenceOOSStat]]:
        clean_states = sorted(
            (
                state for state in states
                if isinstance(state, dict)
                and str(state.get("symbol", ""))
                and int(state.get("timestamp_ms", 0) or 0) > 0
            ),
            key=lambda state: int(state.get("timestamp_ms", 0)),
        )
        train_size = max(2, int(train_size))
        test_size = max(1, int(test_size))
        step_size = max(1, int(step_size if step_size is not None else test_size))
        if len(clean_states) < train_size + test_size:
            return [], []

        observations = self.engine.observations(clean_states, horizons_ms)
        folds: list[EvidenceOOSFold] = []
        oos_values: dict[tuple[str, str, str, str, int], list[float]] = {}
        oos_fold_ids: dict[tuple[str, str, str, str, int], set[int]] = {}
        oos_fold_values: dict[tuple[str, str, str, str, int], dict[int, list[float]]] = {}
        train_fold_counts: dict[tuple[str, str, str, str, int], int] = {}

        fold_id = 0
        start = 0
        while start + train_size + test_size <= len(clean_states):
            train_states = clean_states[start:start + train_size]
            test_states = clean_states[start + train_size:start + train_size + test_size]
            train_start = int(train_states[0]["timestamp_ms"])
            test_start = int(test_states[0]["timestamp_ms"])
            test_end = int(test_states[-1]["timestamp_ms"])

            train_obs = [
                item for item in observations
                if train_start <= item.anchor_timestamp_ms < test_start
                and item.outcome_timestamp_ms < test_start
            ]
            test_obs = [
                item for item in observations
                if test_start <= item.anchor_timestamp_ms <= test_end
                and item.outcome_timestamp_ms <= test_end
            ]

            train_stats = self.engine.aggregate(self._stat_rows(train_obs))
            eligible = {
                self._key(item): item
                for item in train_stats
                if item.eligible
            }
            for key in eligible:
                train_fold_counts[key] = train_fold_counts.get(key, 0) + 1

            for item in test_obs:
                key = self._key(item)
                if key not in eligible:
                    continue
                oos_values.setdefault(key, []).append(item.net_bps)
                oos_fold_ids.setdefault(key, set()).add(fold_id)
                oos_fold_values.setdefault(key, {}).setdefault(fold_id, []).append(item.net_bps)

            folds.append(
                EvidenceOOSFold(
                    fold=fold_id,
                    train_start_ms=train_start,
                    train_end_ms=int(train_states[-1]["timestamp_ms"]),
                    test_start_ms=test_start,
                    test_end_ms=test_end,
                    train_eligible_groups=len(eligible),
                    oos_groups=len({self._key(item) for item in test_obs if self._key(item) in eligible}),
                )
            )
            fold_id += 1
            start += step_size

        results: list[EvidenceOOSStat] = []
        for key, values in sorted(oos_values.items()):
            samples, wins, win_rate, mean, median, lower = summary(values)
            fold_ids = oos_fold_ids.get(key, set())
            fold_count = len(fold_ids)
            fold_values = oos_fold_values.get(key, {})
            positive_fold_ratio = (sum(1 for values_for_fold in fold_values.values() if sum(values_for_fold) / len(values_for_fold) > 0) / fold_count) if fold_count else 0.0
            bootstrap_lower = bootstrap_lower_ci(values, seed_key="|".join(map(str, key)), samples=2000)
            train_eligible_folds = train_fold_counts.get(key, 0)
            validated = (
                fold_count >= self.min_oos_folds
                and train_eligible_folds >= self.min_oos_folds
                and samples >= self.min_oos_samples
                and mean > self.min_oos_mean_net_bps
                and win_rate >= self.min_oos_win_rate
                and lower > self.min_oos_lower_ci_bps
                and bootstrap_lower > self.min_oos_lower_ci_bps
                and positive_fold_ratio >= 0.50
            )
            results.append(
                EvidenceOOSStat(
                    evidence_type=key[0],
                    evidence_name=key[1],
                    symbol=key[2],
                    regime=key[3],
                    horizon_ms=key[4],
                    folds=fold_count,
                    train_eligible_folds=train_eligible_folds,
                    samples=samples,
                    wins=wins,
                    win_rate=round(win_rate, 6),
                    mean_net_bps=round(mean, 6),
                    median_net_bps=round(median, 6),
                    lower_ci_bps=round(lower, 6),
                    bootstrap_lower_ci_bps=round(bootstrap_lower, 6),
                    positive_fold_ratio=round(positive_fold_ratio, 6),
                    validated=validated,
                )
            )
        return folds, results
