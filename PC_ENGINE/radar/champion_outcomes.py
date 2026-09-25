from __future__ import annotations

from dataclasses import dataclass
import json
import math
from PC_ENGINE.radar.evidence_statistics import bootstrap_lower_ci, summary
from pathlib import Path
from typing import Iterable


OutcomeKey = tuple[str, str, str, str, str, int]


@dataclass(frozen=True)
class ChampionOutcomeMetrics:
    candidate_id: str
    version: str
    strategy: str
    symbol: str
    regime: str
    horizon_ms: int
    samples: int
    wins: int
    win_rate: float
    mean_net_bps: float
    median_net_bps: float
    lower_ci_bps: float
    bootstrap_lower_ci_bps: float
    positive_fold_ratio: float
    folds: int
    risk_authorized_only: bool
    validated: bool


@dataclass(frozen=True)
class ChampionOutcomeStressStat:
    candidate_id: str
    version: str
    strategy: str
    symbol: str
    regime: str
    horizon_ms: int
    cost_bps: float
    samples: int
    mean_net_bps: float
    bootstrap_lower_ci_bps: float
    positive_fold_ratio: float
    folds: int
    validated: bool


class ChampionOutcomeAggregator:
    """PAPER-only chronological aggregation and cost-stress evaluation."""

    def __init__(
        self,
        *,
        min_samples: int = 30,
        min_folds: int = 2,
        min_mean_net_bps: float = 0.0,
        min_lower_ci_bps: float = 0.0,
        min_positive_fold_ratio: float = 0.50,
        fold_duration_ms: int = 300_000,
        bootstrap_samples: int = 2000,
    ) -> None:
        self.min_samples = max(1, int(min_samples))
        self.min_folds = max(1, int(min_folds))
        self.min_mean_net_bps = float(min_mean_net_bps)
        self.min_lower_ci_bps = float(min_lower_ci_bps)
        self.min_positive_fold_ratio = float(min_positive_fold_ratio)
        self.fold_duration_ms = max(1, int(fold_duration_ms))
        self.bootstrap_samples = max(200, int(bootstrap_samples))

    @staticmethod
    def _key(row: dict) -> OutcomeKey:
        return (
            str(row["candidate_id"]),
            str(row["version"]),
            str(row["strategy"]),
            str(row["symbol"]),
            str(row.get("regime", "")),
            int(row["horizon_ms"]),
        )

    @staticmethod
    def _validate_row(row: dict) -> None:
        required = {
            "candidate_id", "version", "strategy", "symbol", "horizon_ms",
            "entry_timestamp_ms", "exit_timestamp_ms", "gross_bps", "cost_bps", "net_bps",
            "action", "risk_authorized", "paper_only",
        }
        if not required.issubset(row) or row["paper_only"] is not True:
            raise ValueError("invalid PAPER champion outcome record")
        if str(row["action"]).upper() not in {"BUY", "SELL"}:
            raise ValueError("outcome action must be BUY or SELL")
        for key in ("horizon_ms", "entry_timestamp_ms", "exit_timestamp_ms"):
            if int(row[key]) <= 0:
                raise ValueError(f"{key} must be positive")
        for key in ("gross_bps", "cost_bps", "net_bps"):
            value = float(row[key])
            if not math.isfinite(value):
                raise ValueError(f"{key} must be finite")
        if float(row["cost_bps"]) < 0:
            raise ValueError("cost_bps cannot be negative")
        if int(row["exit_timestamp_ms"]) < int(row["entry_timestamp_ms"]):
            raise ValueError("outcome timestamps must be chronological")

    @staticmethod
    def load(path: str | Path) -> list[dict]:
        file_path = Path(path)
        if not file_path.exists():
            return []
        rows: list[dict] = []
        for line in file_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                ChampionOutcomeAggregator._validate_row(row)
                rows.append(row)
        return rows

    def _metrics(self, rows: list[dict], *, risk_authorized_only: bool) -> ChampionOutcomeMetrics:
        rows = sorted(rows, key=lambda row: int(row["exit_timestamp_ms"]))
        if risk_authorized_only:
            rows = [row for row in rows if bool(row["risk_authorized"])]
        values = [float(row["net_bps"]) for row in rows]
        samples, wins, win_rate, mean, med, lower = summary(values)
        folds: dict[int, list[float]] = {}
        for row, value in zip(rows, values):
            fold = int(row["exit_timestamp_ms"]) // self.fold_duration_ms
            folds.setdefault(fold, []).append(value)
        positive_ratio = (
            sum(sum(fold_values) / len(fold_values) > 0 for fold_values in folds.values()) / len(folds)
            if folds else 0.0
        )
        key = self._key(rows[0]) if rows else ("", "", "", "", "", 0)
        bootstrap = bootstrap_lower_ci(values, seed_key="|".join(map(str, key)), samples=self.bootstrap_samples)
        validated = (
            samples >= self.min_samples
            and len(folds) >= self.min_folds
            and mean > self.min_mean_net_bps
            and lower > self.min_lower_ci_bps
            and bootstrap > self.min_lower_ci_bps
            and positive_ratio >= self.min_positive_fold_ratio
        )
        return ChampionOutcomeMetrics(
            candidate_id=key[0], version=key[1], strategy=key[2], symbol=key[3],
            regime=key[4], horizon_ms=key[5], samples=samples, wins=wins,
            win_rate=round(wins / samples, 6) if samples else 0.0,
            mean_net_bps=round(mean, 6), median_net_bps=round(float(med), 6),
            lower_ci_bps=round(lower, 6), bootstrap_lower_ci_bps=round(bootstrap, 6),
            positive_fold_ratio=round(positive_ratio, 6), folds=len(folds),
            risk_authorized_only=risk_authorized_only, validated=validated,
        )

    def aggregate(
        self,
        rows: Iterable[dict],
        *,
        risk_authorized_only: bool = True,
    ) -> list[ChampionOutcomeMetrics]:
        clean = []
        for row in rows:
            self._validate_row(row)
            clean.append(dict(row))
        groups: dict[OutcomeKey, list[dict]] = {}
        for row in clean:
            groups.setdefault(self._key(row), []).append(row)
        return [
            self._metrics(group, risk_authorized_only=risk_authorized_only)
            for _, group in sorted(groups.items())
        ]

    def stress(
        self,
        rows: Iterable[dict],
        *,
        costs_bps: tuple[float, ...] = (28.0, 35.0, 42.0, 56.0),
        risk_authorized_only: bool = True,
    ) -> list[ChampionOutcomeStressStat]:
        clean = []
        for row in rows:
            self._validate_row(row)
            if not risk_authorized_only or bool(row["risk_authorized"]):
                clean.append(dict(row))
        scenarios = tuple(sorted({float(cost) for cost in costs_bps}))
        if not scenarios or any(not math.isfinite(cost) or cost < 0 for cost in scenarios):
            raise ValueError("cost scenarios must be finite and non-negative")
        groups: dict[OutcomeKey, list[dict]] = {}
        for row in clean:
            groups.setdefault(self._key(row), []).append(row)

        results: list[ChampionOutcomeStressStat] = []
        for cost in scenarios:
            for key, group in sorted(groups.items()):
                ordered = sorted(group, key=lambda row: int(row["exit_timestamp_ms"]))
                values = [float(row["gross_bps"]) - cost for row in ordered]
                samples = len(values)
                mean = sum(values) / samples if samples else 0.0
                folds: dict[int, list[float]] = {}
                for row, value in zip(ordered, values):
                    folds.setdefault(int(row["exit_timestamp_ms"]) // self.fold_duration_ms, []).append(value)
                positive_ratio = (
                    sum(sum(v) / len(v) > 0 for v in folds.values()) / len(folds)
                    if folds else 0.0
                )
                bootstrap = bootstrap_lower_ci(values, seed_key=f"{'|'.join(map(str, key))}|{cost:g}", samples=self.bootstrap_samples)
                validated = (
                    samples >= self.min_samples
                    and len(folds) >= self.min_folds
                    and mean > self.min_mean_net_bps
                    and bootstrap > self.min_lower_ci_bps
                    and positive_ratio >= self.min_positive_fold_ratio
                )
                results.append(
                    ChampionOutcomeStressStat(
                        candidate_id=key[0], version=key[1], strategy=key[2],
                        symbol=key[3], regime=key[4], horizon_ms=key[5],
                        cost_bps=cost, samples=samples, mean_net_bps=round(mean, 6),
                        bootstrap_lower_ci_bps=round(bootstrap, 6),
                        positive_fold_ratio=round(positive_ratio, 6),
                        folds=len(folds), validated=validated,
                    )
                )
        return results

    @staticmethod
    def robustness(
        stats: Iterable[ChampionOutcomeStressStat],
        *,
        min_cost_scenarios: int = 3,
    ) -> dict[OutcomeKey, bool]:
        grouped: dict[OutcomeKey, list[ChampionOutcomeStressStat]] = {}
        for stat in stats:
            key = (
                stat.candidate_id, stat.version, stat.strategy,
                stat.symbol, stat.regime, stat.horizon_ms,
            )
            grouped.setdefault(key, []).append(stat)
        required = max(1, int(min_cost_scenarios))
        return {
            key: len(rows) >= required and all(row.validated for row in rows)
            for key, rows in grouped.items()
        }
