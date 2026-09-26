from __future__ import annotations

import json
from dataclasses import asdict
import os
import time
from pathlib import Path

from PC_ENGINE.core.real_readiness import RealReadinessGate
from PC_ENGINE.core.paper_review import PaperReview
from PC_ENGINE.radar.evidence_ledger import EvidenceLedger
from PC_ENGINE.learning.evidence_learning_loop import PaperEvidenceLearningLoop


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
        self.max_evidence_age_seconds = max(60, int(readiness.get("max_evidence_age_seconds", 900)))
        self.max_validation_age_seconds = max(300, int(readiness.get("max_validation_age_seconds", 86400)))
        self.history_path = Path(readiness.get("history_path", "PC_ENGINE/data/radar/readiness_history.jsonl"))
        self.history_enabled = bool(readiness.get("history_enabled", True))
        self.history_limit = max(1, int(readiness.get("history_limit", 1000)))

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


    @staticmethod
    def _latest_timestamp_ms(rows: list[dict]) -> int:
        timestamps = []
        for row in rows:
            for key in ("timestamp_ms", "observed_ts_ms", "ts_ms", "created_at_ms"):
                try:
                    value = int(row.get(key, 0) or 0)
                except (TypeError, ValueError):
                    value = 0
                if value > 0:
                    timestamps.append(value)
                    break
        return max(timestamps, default=0)

    def _evidence_fresh(self, rows: list[dict], now_ms: int) -> tuple[bool, str]:
        latest = self._latest_timestamp_ms(rows)
        if not latest:
            return False, "missing evidence timestamp"
        age_ms = max(0, now_ms - latest)
        limit_ms = self.max_evidence_age_seconds * 1000
        return age_ms <= limit_ms, f"age_ms={age_ms}; max_ms={limit_ms}"

    def _validation_fresh(self, path: Path, now_ms: int) -> tuple[bool, str]:
        if not path.exists():
            return False, "artifact missing"
        try:
            age = max(0, now_ms / 1000.0 - path.stat().st_mtime)
        except OSError:
            return False, "artifact stat failed"
        return age <= self.max_validation_age_seconds, f"age_s={int(age)}; max_s={self.max_validation_age_seconds}"

    def _persist_history(self, payload: dict, now_ms: int) -> None:
        if not self.history_enabled:
            return
        row = {"timestamp_ms": now_ms, "status": payload.get("status"), "ready": bool(payload.get("ready")), "blockers": list(payload.get("blockers", [])), "paper_review": payload.get("paper_review", {})}
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            rows = self._read_jsonl(self.history_path)
            rows.append(row)
            rows = rows[-self.history_limit:]
            tmp = self.history_path.with_suffix(self.history_path.suffix + ".tmp")
            tmp.write_text("".join(json.dumps(item, sort_keys=True, separators=(",", ":")) + "\n" for item in rows), encoding="utf-8")
            os.replace(tmp, self.history_path)
        except OSError:
            return

    def history(self) -> dict:
        rows = self._read_jsonl(self.history_path)
        return {"enabled": self.history_enabled, "path": str(self.history_path), "records": len(rows), "latest": rows[-1] if rows else None, "ready_count": sum(bool(x.get("ready")) for x in rows), "blocked_count": sum(x.get("status") == "LOCKED" for x in rows)}

    def collect(self, engine, persist_history: bool = True) -> dict:
        now_ms = int(__import__('time').time() * 1000)
        states = self._read_jsonl(self.data_dir / "market_states.jsonl")
        outcomes = self._read_jsonl(self.data_dir / "state_outcomes.jsonl")
        state_fresh, state_fresh_detail = self._evidence_fresh(states, now_ms)
        outcome_fresh, outcome_fresh_detail = self._evidence_fresh(outcomes, now_ms)
        outcome_samples = sum(int(row.get("samples", 0) or 0) for row in outcomes)
        eligible = sum(bool(row.get("eligible")) for row in outcomes)
        validation_dir = self.data_dir / "validation"
        preflight_ok = bool(engine.state.preflight.get("ok")) if engine.state.preflight else False
        watchdog_ok = bool(engine.state.watchdog.get("ok", False)) if engine.state.watchdog else False
        recovery_ok = (
            not bool(engine.state.open_positions)
            or (self.data_dir / "recovery_heartbeat.json").exists()
        )
        pending_orders_ok = not bool(engine.state.pending_orders)
        execution_intents_ok = not bool(engine.state.execution_intents)
        critical_errors = sum(1 for line in engine.state.logs if "CRITICAL" in line.upper())

        validation_paths = {
            "walk_forward": validation_dir / "walk_forward.json",
            "regime_validation": validation_dir / "regime_validation.json",
            "execution_test": validation_dir / "execution_test.json",
            "l2_oos": self.data_dir / "l2_oos_validation.json",
        }
        validation_fresh = {}
        for name, path in validation_paths.items():
            validation_fresh[name] = self._validation_fresh(path, now_ms)

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
        reconciliation_ok = (
            bool(reconciliation)
            and float(reconciliation.get("unreconciled_ratio", 0.0) or 0.0) == 0.0
        )
        if not self.require_reconciliation:
            reconciliation_ok = True

        credentials_ok, credentials_detail = self._live_credentials_ok(engine)
        report = self.gate.evaluate(
            mode=engine.mode,
            preflight_ok=preflight_ok,
            state_samples=len(states),
            outcome_samples=outcome_samples,
            eligible_outcomes=eligible,
            walk_forward_ok=self._validation_status(validation_dir / "walk_forward.json") and validation_fresh["walk_forward"][0] and state_fresh,
            regime_validation_ok=self._validation_status(validation_dir / "regime_validation.json") and validation_fresh["regime_validation"][0] and state_fresh,
            watchdog_ok=watchdog_ok,
            recovery_ok=recovery_ok,
            pending_orders_ok=pending_orders_ok,
            execution_intents_ok=execution_intents_ok,
            execution_test_ok=self._validation_status(validation_dir / "execution_test.json") and validation_fresh["execution_test"][0],
            critical_errors=critical_errors,
            credentials_ok=credentials_ok,
            credentials_detail=credentials_detail,
            l2_oos_ok=l2_ok and validation_fresh["l2_oos"][0] and outcome_fresh,
            l2_oos_detail=f"stable_rows={l2_stable}",
            reconciliation_ok=reconciliation_ok,
            reconciliation_detail=f"unreconciled_ratio={reconciliation.get('unreconciled_ratio', 'missing')}",
            account_reconciliation=engine.state.account_reconciliation or None,
            min_state_samples=self.min_state_samples,
            min_outcome_samples=self.min_outcome_samples,
            min_eligible_outcomes=self.min_eligible_outcomes,
        )
        payload = report.to_dict()
        payload["evidence"] = {
            "market_state_rows": len(states),
            "outcome_rows": len(outcomes),
            "outcome_samples": outcome_samples,
            "eligible_outcomes": eligible,
            "l2_stable_rows": l2_stable,
            "l2_oos_required": self.require_l2_oos,
            "paper_reconciliation_required": self.require_reconciliation,
            "reconciliation_path": str(reconciliation_path),
            "pending_orders_clear": pending_orders_ok,
            "execution_intents_clear": execution_intents_ok,
            "required_market_state_rows": self.min_state_samples,
            "required_outcome_samples": self.min_outcome_samples,
            "required_eligible_outcomes": self.min_eligible_outcomes,
            "data_dir": str(self.data_dir),
            "max_evidence_age_seconds": self.max_evidence_age_seconds,
            "max_validation_age_seconds": self.max_validation_age_seconds,
            "state_fresh": state_fresh,
            "state_fresh_detail": state_fresh_detail,
            "outcome_fresh": outcome_fresh,
            "outcome_fresh_detail": outcome_fresh_detail,
            "validation_freshness": validation_fresh,
        }
        try:
            ledger_path = engine.config.get("evidence", {}).get(
                "ledger_path", "PC_ENGINE/data/radar/evidence_ledger.jsonl"
            )
            ledger_records = EvidenceLedger.load(ledger_path)
            audit = EvidenceLedger.audit_report(ledger_records)
            learning = PaperEvidenceLearningLoop().evaluate(ledger_records).to_dict()
            champion = {"eligible": audit.eligible_records > 0, "reason": "eligible evidence records present"}
            execution = {
                "ok": pending_orders_ok and execution_intents_ok and reconciliation_ok,
                "detail": "paper execution state reconciled",
            }
            payload["paper_review"] = PaperReview.evaluate(
                payload, audit=asdict(audit), learning=learning,
                champion=champion, execution=execution,
            )
        except (OSError, ValueError, TypeError):
            payload["paper_review"] = PaperReview.evaluate(
                payload, audit={}, learning={}, champion={},
                execution={
                    "ok": pending_orders_ok and execution_intents_ok and reconciliation_ok,
                    "detail": "paper execution state reconciled",
                },
            )
        if persist_history:
            self._persist_history(payload, now_ms)
        return payload
