from __future__ import annotations

import json
import os
from pathlib import Path

from PC_ENGINE.core.real_readiness import RealReadinessGate


class RealReadinessService:
    """Collect evidence for protected REAL review. Never authorizes an order."""

    def __init__(self, config: dict):
        readiness = config.get("real_readiness", {})
        self.data_dir = Path(readiness.get("data_dir", "PC_ENGINE/data/radar"))
        self.gate = RealReadinessGate()
        self.min_state_samples = max(1, int(readiness.get("min_state_samples", 1000)))
        self.min_outcome_samples = max(1, int(readiness.get("min_outcome_samples", 1000)))
        self.min_eligible_outcomes = max(1, int(readiness.get("min_eligible_outcomes", 1)))
        self.require_l2_oos = bool(readiness.get("require_l2_oos_validation", True))
        self.require_reconciliation = bool(readiness.get("require_paper_reconciliation", True))

    @staticmethod
    def _read_jsonl(path: Path) -> list[dict]:
        if not path.exists():
            return []
        rows = []
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
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
    def _read_json(path: Path) -> dict:
        if not path.exists():
            return {}
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    @staticmethod
    def _validation_status(path: Path) -> bool:
        payload = RealReadinessService._read_json(path)
        return bool(payload.get("ok") is True or payload.get("passed") is True)

    def _live_credentials_ok(self, engine) -> tuple[bool, str]:
        if str(engine.mode).upper() != "REAL":
            return True, "not required while in PAPER"
        missing = []
        for name, cfg in engine.config.get("exchanges", {}).items():
            if not cfg.get("enabled", False):
                continue
            key_env = str(cfg.get("key_env", ""))
            secret_env = str(cfg.get("private_env", ""))
            if not key_env or not secret_env or not os.getenv(key_env) or not os.getenv(secret_env):
                missing.append(name)
        if missing:
            return False, f"missing API credentials: {','.join(missing)}"
        return True, "configured enabled exchange credentials present"

    def collect(self, engine) -> dict:
        states = self._read_jsonl(self.data_dir / "market_states.jsonl")
        outcomes = self._read_jsonl(self.data_dir / "state_outcomes.jsonl")
        outcome_samples = sum(int(row.get("samples", 0) or 0) for row in outcomes)
        eligible = sum(bool(row.get("eligible")) for row in outcomes)
        validation_dir = self.data_dir / "validation"
        preflight_ok = bool(engine.state.preflight.get("ok")) if engine.state.preflight else False
        watchdog_ok = bool(engine.state.watchdog.get("ok", False)) if engine.state.watchdog else False
        recovery_ok = not bool(engine.state.open_positions) or (self.data_dir / "recovery_heartbeat.json").exists()
        critical_errors = sum(1 for line in engine.state.logs if "CRITICAL" in line.upper())

        l2_payload = self._read_json(self.data_dir / "l2_oos_validation.json")
        l2_rows = l2_payload.get("rows", []) if isinstance(l2_payload.get("rows", []), list) else []
        l2_stable = sum(bool(row.get("stable")) for row in l2_rows)
        l2_ok = l2_stable > 0 if self.require_l2_oos else True

        paper_cfg = engine.config.get("paper", {})
        reconciliation_path = Path(paper_cfg.get(
            "reconciliation_path",
            "PC_ENGINE/data/paper/autonomous_reconciliation.json",
        ))
        reconciliation = self._read_json(reconciliation_path)
        reconciliation_ok = bool(reconciliation) and float(reconciliation.get("unreconciled_ratio", 0.0) or 0.0) == 0.0
        if not self.require_reconciliation:
            reconciliation_ok = True

        credentials_ok, credentials_detail = self._live_credentials_ok(engine)
        report = self.gate.evaluate(
            mode=engine.mode, preflight_ok=preflight_ok,
            state_samples=len(states), outcome_samples=outcome_samples,
            eligible_outcomes=eligible,
            walk_forward_ok=self._validation_status(validation_dir / "walk_forward.json"),
            regime_validation_ok=self._validation_status(validation_dir / "regime_validation.json"),
            watchdog_ok=watchdog_ok, recovery_ok=recovery_ok,
            execution_test_ok=self._validation_status(validation_dir / "execution_test.json"),
            critical_errors=critical_errors, credentials_ok=credentials_ok,
            credentials_detail=credentials_detail, l2_oos_ok=l2_ok,
            l2_oos_detail=f"stable_rows={l2_stable}",
            reconciliation_ok=reconciliation_ok,
            reconciliation_detail=f"unreconciled_ratio={reconciliation.get('unreconciled_ratio', 'missing')}",
            min_state_samples=self.min_state_samples,
            min_outcome_samples=self.min_outcome_samples,
            min_eligible_outcomes=self.min_eligible_outcomes,
        )
        payload = report.to_dict()
        payload["evidence"] = {
            "market_state_rows": len(states), "outcome_rows": len(outcomes),
            "outcome_samples": outcome_samples, "eligible_outcomes": eligible,
            "l2_stable_rows": l2_stable, "l2_oos_required": self.require_l2_oos,
            "paper_reconciliation_required": self.require_reconciliation,
            "reconciliation_path": str(reconciliation_path),
            "required_market_state_rows": self.min_state_samples,
            "required_outcome_samples": self.min_outcome_samples,
            "required_eligible_outcomes": self.min_eligible_outcomes,
            "data_dir": str(self.data_dir),
        }
        return payload
