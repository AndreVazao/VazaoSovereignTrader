from __future__ import annotations

from pathlib import Path
import re

from PC_ENGINE.radar.evidence_ledger import (
    EvidenceLedger,
    EvidenceLedgerRecord,
    EvidencePlaneSummary,
)
from PC_ENGINE.radar.evidence_outcomes import EvidenceOutcomeEngine
from PC_ENGINE.radar.evidence_statistics import bootstrap_lower_ci
from PC_ENGINE.radar.evidence_stress import EvidenceStatisticalStressTester


class PaperEvidenceLedgerBuilder:
    """Build immutable PAPER evidence records from the live market-state stream.

    This component only writes research evidence. It never authorizes trades,
    changes mode, or changes risk state.
    """

    def __init__(self, settings: dict):
        evidence = dict(settings.get("evidence", {}))
        self.path = Path(
            evidence.get("ledger_path", "PC_ENGINE/data/radar/evidence_ledger.jsonl")
        )
        self.enabled = bool(evidence.get("ledger_writer_enabled", True))
        self.interval_cycles = max(1, int(evidence.get("ledger_writer_interval_cycles", 12)))
        self.min_states = max(30, int(evidence.get("ledger_min_states", 300)))
        self.train_size = max(2, int(evidence.get("ledger_train_size", 200)))
        self.test_size = max(1, int(evidence.get("ledger_test_size", 100)))
        self.step_size = max(1, int(evidence.get("ledger_step_size", self.test_size)))
        self.horizons_ms = tuple(
            int(value) for value in evidence.get(
                "ledger_horizons_ms", (5000, 15000, 60000)
            )
        )
        self.costs_bps = tuple(
            float(value) for value in evidence.get(
                "ledger_costs_bps", (28.0, 35.0, 42.0, 56.0)
            )
        )
        self.min_cost_scenarios = max(
            1, int(evidence.get("ledger_min_cost_scenarios", 3))
        )
        self._last_state_count = 0

    @staticmethod
    def _candidate_id(evidence_type: str, evidence_name: str, horizon_ms: int) -> str:
        raw = f"{evidence_type}:{evidence_name}:{horizon_ms}"
        return re.sub(r"[^A-Za-z0-9_.:-]+", "_", raw)

    @staticmethod
    def _state_window(states: list[dict], symbol: str, regime: str) -> tuple[int, int]:
        timestamps = [
            int(row.get("timestamp_ms", 0) or 0)
            for row in states
            if row.get("symbol") == symbol
            and str(row.get("regime", "")) == regime
            and int(row.get("timestamp_ms", 0) or 0) > 0
        ]
        if not timestamps:
            return 1, 1
        return min(timestamps), max(timestamps)

    def _latest_by_key(self) -> dict[tuple[str, str, str, str, int], int]:
        latest: dict[tuple[str, str, str, str, int], int] = {}
        for record in EvidenceLedger.load(self.path):
            key = (
                record.candidate_id,
                record.version,
                record.symbol,
                record.regime,
                record.horizon_ms,
            )
            latest[key] = max(latest.get(key, 0), record.data_end_ms)
        return latest

    def refresh(self, states: list[dict], *, force: bool = False) -> int:
        if not self.enabled or len(states) < self.min_states:
            return 0
        if not force and len(states) < self._last_state_count + self.test_size:
            return 0

        clean_states = sorted(
            (
                row for row in states
                if isinstance(row, dict)
                and str(row.get("symbol", "")).strip()
                and int(row.get("timestamp_ms", 0) or 0) > 0
                and float(row.get("price", 0.0) or 0.0) > 0
            ),
            key=lambda row: int(row.get("timestamp_ms", 0)),
        )
        if len(clean_states) < self.min_states:
            return 0

        latest = self._latest_by_key()
        outcome_engine = EvidenceOutcomeEngine(
            cost_bps=min(self.costs_bps) if self.costs_bps else 28.0,
            min_samples=30,
        )
        observations = outcome_engine.observations(
            clean_states, horizons_ms=self.horizons_ms
        )
        stats = outcome_engine.aggregate(
            [
                type("_Row", (), {
                    "evidence_type": item.evidence_type,
                    "evidence_name": item.evidence_name,
                    "symbol": item.symbol,
                    "regime": item.regime,
                    "horizon_ms": item.horizon_ms,
                    "samples": 1,
                    "wins": int(item.net_bps > 0),
                    "win_rate": float(item.net_bps > 0),
                    "mean_net_bps": item.net_bps,
                    "median_net_bps": item.net_bps,
                    "lower_ci_bps": item.net_bps,
                    "eligible": False,
                })()
                for item in observations
            ]
        )
        if not stats:
            self._last_state_count = len(clean_states)
            return 0

        stress = EvidenceStatisticalStressTester(
            costs_bps=self.costs_bps,
        ).validate(
            clean_states,
            train_size=self.train_size,
            test_size=self.test_size,
            step_size=self.step_size,
            horizons_ms=self.horizons_ms,
        )
        robustness = EvidenceStatisticalStressTester.robustness(
            stress, min_cost_scenarios=self.min_cost_scenarios
        )

        written = 0
        for stat in stats:
            key = (
                stat.evidence_type,
                stat.evidence_name,
                stat.symbol,
                stat.regime,
                stat.horizon_ms,
            )
            candidate_id = self._candidate_id(*key[:2], key[4])
            version = "paper-runtime-v1"
            data_start_ms, data_end_ms = self._state_window(
                clean_states, stat.symbol, stat.regime
            )
            latest_key = (candidate_id, version, stat.symbol, stat.regime, stat.horizon_ms)
            if not force and latest.get(latest_key, 0) >= data_end_ms:
                continue

            values = [
                item.net_bps
                for item in observations
                if (
                    item.evidence_type,
                    item.evidence_name,
                    item.symbol,
                    item.regime,
                    item.horizon_ms,
                ) == key
            ]
            bootstrap_lower = bootstrap_lower_ci(
                values,
                seed_key="|".join(map(str, key)),
                samples=2000,
            ) if values else 0.0

            stress_rows = [
                row for row in stress
                if (
                    row.evidence_type,
                    row.evidence_name,
                    row.symbol,
                    row.regime,
                    row.horizon_ms,
                ) == key
            ]
            validated_stress = [row for row in stress_rows if row.validated]
            robust = bool(robustness.get(key, False))
            durable_pass = bool(
                stat.eligible
                and stat.lower_ci_bps > 0.0
                and bootstrap_lower > 0.0
            )
            eligible = durable_pass and robust
            reason = (
                "eligible PAPER evidence with durable and chronological OOS cost-stress validation"
                if eligible
                else "PAPER evidence has not passed all durable/OOS/cost-stress gates"
            )
            durable = EvidencePlaneSummary(
                name="durable_outcome",
                status="PASS" if durable_pass else "FAIL",
                samples=stat.samples,
                scenarios=1,
                validated_scenarios=int(durable_pass),
                mean_net_bps=stat.mean_net_bps,
                lower_ci_bps=stat.lower_ci_bps,
                bootstrap_lower_ci_bps=bootstrap_lower,
                positive_fold_ratio=1.0 if durable_pass else 0.0,
                folds=0,
            )
            worst_bootstrap = min(
                (float(row.bootstrap_lower_ci_bps) for row in stress_rows),
                default=0.0,
            )
            worst_mean = min(
                (float(row.mean_net_bps) for row in stress_rows),
                default=0.0,
            )
            worst_fold_ratio = min(
                (float(row.positive_fold_ratio) for row in stress_rows),
                default=0.0,
            )
            oos = EvidencePlaneSummary(
                name="chronological_oos",
                status="PASS" if robust else "FAIL",
                samples=min((int(row.samples) for row in stress_rows), default=0),
                scenarios=len(stress_rows),
                validated_scenarios=len(validated_stress),
                mean_net_bps=worst_mean,
                lower_ci_bps=0.0,
                bootstrap_lower_ci_bps=worst_bootstrap,
                positive_fold_ratio=worst_fold_ratio,
                folds=0,
            )
            EvidenceLedger.append(
                self.path,
                EvidenceLedgerRecord(
                    created_at_ms=max(data_end_ms, 1),
                    candidate_id=candidate_id,
                    version=version,
                    strategy="paper_evidence_runtime",
                    symbol=stat.symbol,
                    regime=stat.regime,
                    horizon_ms=stat.horizon_ms,
                    eligible=eligible,
                    reason=reason,
                    reason_codes=EvidenceLedger.reason_codes(reason),
                    data_start_ms=max(data_start_ms, 1),
                    data_end_ms=max(data_end_ms, data_start_ms, 1),
                    state_count=len(clean_states),
                    outcome_count=stat.samples,
                    durable_outcome=durable,
                    chronological_oos=oos,
                    source_digest="0" * 64,
                ),
            )
            written += 1

        self._last_state_count = len(clean_states)
        return written
