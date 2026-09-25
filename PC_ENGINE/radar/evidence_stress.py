from __future__ import annotations

from dataclasses import dataclass

from PC_ENGINE.radar.evidence_oos import EvidenceWalkForwardValidator


@dataclass(frozen=True)
class EvidenceStressStat:
    evidence_type: str
    evidence_name: str
    symbol: str
    regime: str
    horizon_ms: int
    cost_bps: float
    samples: int
    mean_net_bps: float
    bootstrap_lower_ci_bps: float
    positive_fold_ratio: float
    validated: bool


class EvidenceStatisticalStressTester:
    """Run the same chronological OOS protocol across execution-cost scenarios.

    This is a research gate only. It never changes Risk Engine authorization.
    """

    def __init__(
        self,
        *,
        costs_bps: tuple[float, ...] = (28.0, 35.0, 42.0, 56.0),
        validator_kwargs: dict | None = None,
    ) -> None:
        self.costs_bps = tuple(sorted({max(0.0, float(value)) for value in costs_bps}))
        if not self.costs_bps:
            raise ValueError("costs_bps must not be empty")
        self.validator_kwargs = dict(validator_kwargs or {})

    def validate(
        self,
        states: list[dict],
        *,
        train_size: int = 200,
        test_size: int = 100,
        step_size: int | None = None,
        horizons_ms: tuple[int, ...] = (1000, 5000, 15000, 60000, 300000),
    ) -> list[EvidenceStressStat]:
        results: list[EvidenceStressStat] = []
        for cost_bps in self.costs_bps:
            validator = EvidenceWalkForwardValidator(
                cost_bps=cost_bps,
                **self.validator_kwargs,
            )
            _, stats = validator.validate(
                states,
                train_size=train_size,
                test_size=test_size,
                step_size=step_size,
                horizons_ms=horizons_ms,
            )
            for stat in stats:
                results.append(
                    EvidenceStressStat(
                        evidence_type=stat.evidence_type,
                        evidence_name=stat.evidence_name,
                        symbol=stat.symbol,
                        regime=stat.regime,
                        horizon_ms=stat.horizon_ms,
                        cost_bps=cost_bps,
                        samples=stat.samples,
                        mean_net_bps=stat.mean_net_bps,
                        bootstrap_lower_ci_bps=stat.bootstrap_lower_ci_bps,
                        positive_fold_ratio=stat.positive_fold_ratio,
                        validated=stat.validated,
                    )
                )
        return results

    @staticmethod
    def robustness(
        stats: list[EvidenceStressStat],
        *,
        min_cost_scenarios: int = 3,
    ) -> dict[tuple[str, str, str, str, int], bool]:
        grouped: dict[tuple[str, str, str, str, int], list[EvidenceStressStat]] = {}
        for stat in stats:
            key = (
                stat.evidence_type,
                stat.evidence_name,
                stat.symbol,
                stat.regime,
                stat.horizon_ms,
            )
            grouped.setdefault(key, []).append(stat)
        required = max(1, int(min_cost_scenarios))
        return {
            key: len(rows) >= required and all(row.validated for row in rows)
            for key, rows in grouped.items()
        }
