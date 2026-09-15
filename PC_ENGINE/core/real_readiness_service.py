from __future__ import annotations

import json
from pathlib import Path

from PC_ENGINE.core.real_readiness import RealReadinessGate, ReadinessReport


class RealReadinessService:
    """Collect local evidence and evaluate the protected-REAL gate.

    Missing artifacts are reported as insufficient evidence; nothing is
    inferred or fabricated. This service is descriptive and non-authorizing.
    """

    def __init__(self, config: dict):
        readiness = config.get("real_readiness", {})
        self.data_dir = Path(readiness.get("data_dir", "PC_ENGINE/data/radar"))
        self.min_state_samples = int(readiness.get("min_state_samples", 1000))
        self.min_outcome_samples = int(readiness.get("min_outcome_samples", 1000))
        self.min_eligible_outcomes = int(readiness.get("min_eligible_outcomes", 1))
        self.gate = RealReadinessGate()

    @staticmethod
    def _read_jsonl(path: Path) -> list[dict]:
        if not path.exists():
            return []
        rows: list[dict] = []
        try:
            with path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    try:
                        value = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(value, dict):
                        rows.append(value)
        except OSError:
            return []
        return rows

    @staticmethod
    def _validation_status(path: Path) -> bool:
        if not path.exists():
            return False
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False
        return bool(payload.get("ok") is True or payload.get("passed") is True)

    def collect(self, engine) -> dict:
        states = self._read_jsonl(self.data_dir / "market_states.jsonl")
        outcomes = self._read_jsonl(self.data_dir / "state_outcomes.jsonl")
        eligible = [row for row in outcomes if bool(row.get("eligible"))]
        outcome_samples = sum(int(row.get("samples", 0) or 0) for row in outcomes)
        validation_dir = self.data_dir / "validation"

        preflight_ok = bool(engine.state.preflight.get("ok")) if engine.state.preflight else False
        watchdog_ok = bool(engine.state.watchdog.get("ok", False)) if engine.state.watchdog else False
        recovery_ok = not bool(engine.state.open_positions) or (self.data_dir / "recovery_heartbeat.json").exists()
        critical_errors = sum(1 for line in engine.state.logs if "CRITICAL" in line.upper())

        report: ReadinessReport = self.gate.evaluate(
            mode=engine.mode,
            preflight_ok=preflight_ok,
            state_samples=len(states),
            outcome_samples=outcome_samples,
            eligible_outcomes=len(eligible),
            walk_forward_ok=self._validation_status(validation_dir / "walk_forward.json"),
            regime_validation_ok=self._validation_status(validation_dir / "regime_validation.json"),
            watchdog_ok=watchdog_ok,
            recovery_ok=recovery_ok,
            execution_test_ok=self._validation_status(validation_dir / "execution_test.json"),
            critical_errors=critical_errors,
        )
        payload = report.to_dict()
        payload["evidence"] = {
            "market_state_rows": len(states),
            "outcome_rows": len(outcomes),
            "outcome_samples": outcome_samples,
            "eligible_outcomes": len(eligible),
            "required_market_state_rows": self.min_state_samples,
            "required_outcome_samples": self.min_outcome_samples,
            "required_eligible_outcomes": self.min_eligible_outcomes,
            "data_dir": str(self.data_dir),
        }
        return payload
