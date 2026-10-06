from __future__ import annotations

import json
from dataclasses import asdict
import os
import time
from pathlib import Path

from PC_ENGINE.core.real_readiness import RealReadinessGate
from PC_ENGINE.core.venue_capabilities import VenueCapabilityRegistry, build_real_execution_requirements
from PC_ENGINE.core.capability_evidence_store import CapabilityEvidenceStore
from PC_ENGINE.core.paper_review import PaperReview
from PC_ENGINE.radar.evidence_ledger import EvidenceLedger
from PC_ENGINE.learning.evidence_learning_loop import PaperEvidenceLearningLoop
from PC_ENGINE.core.readiness_trend import ReadinessTrendEngine
from PC_ENGINE.core.readiness_scorecard import ReadinessStabilityScorecard
from PC_ENGINE.core.readiness_timeline import ReadinessDiagnosticTimeline


class RealReadinessService:
    """Collect evidence for protected REAL review. Never authorizes an order."""

    def __init__(self, config: dict):
        readiness = config.get("real_readiness", {})
        self.data_dir = Path(readiness.get("data_dir", "PC_ENGINE/data/radar"))
        self.gate = RealReadinessGate()
        self.require_verified_venue_capabilities = bool(readiness.get("require_verified_venue_capabilities", False))
        self.venue_capabilities = VenueCapabilityRegistry(readiness.get("venue_capabilities", {}))
        self.min_state_samples = max(1, int(readiness.get("min_state_samples", 1000)))
        self.min_outcome_samples = max(1, int(readiness.get("min_outcome_samples", 1000)))
        self.min_eligible_outcomes = max(1, int(readiness.get("min_eligible_outcomes", 1)))
        self.min_eligible_outcome_samples = max(1, int(readiness.get("min_eligible_outcome_samples", 300)))
        self.min_eligible_evidence_records = max(1, int(readiness.get("min_eligible_evidence_records", 3)))
        self.min_evidence_symbols = max(1, int(readiness.get("min_evidence_symbols", 2)))
        self.min_evidence_regimes = max(1, int(readiness.get("min_evidence_regimes", 2)))
        self.min_evidence_span_seconds = max(0, int(readiness.get("min_evidence_span_seconds", 21600)))
        self.min_recent_evidence_records = max(1, int(readiness.get("min_recent_evidence_records", 3)))
        self.min_recent_eligible_ratio = min(1.0, max(0.0, float(readiness.get("min_recent_eligible_ratio", 1.0))))
        self.require_positive_economic_ci = bool(readiness.get("require_positive_economic_ci", True))
        self.require_l2_oos = bool(readiness.get("require_l2_oos_validation", True))
        self.require_reconciliation = bool(readiness.get("require_paper_reconciliation", True))
        self.max_evidence_age_seconds = max(60, int(readiness.get("max_evidence_age_seconds", 900)))
        self.max_validation_age_seconds = max(300, int(readiness.get("max_validation_age_seconds", 86400)))
        self.history_path = Path(readiness.get("history_path", "PC_ENGINE/data/radar/readiness_history.jsonl"))
        self.history_enabled = bool(readiness.get("history_enabled", True))
        self.history_limit = max(1, int(readiness.get("history_limit", 1000)))
        self.trend_min_samples = max(1, int(readiness.get("trend_min_samples", 10)))
        self.trend_recent_window = max(1, int(readiness.get("trend_recent_window", 5)))
        self.trend_min_span_seconds = max(0, int(readiness.get("trend_min_span_seconds", 300)))
        self.trend_degradation_threshold = max(0.0, float(readiness.get("trend_degradation_threshold", 0.20)))
        self.trend_recovery_threshold = max(0.0, float(readiness.get("trend_recovery_threshold", 0.20)))
        self.trend_required_consecutive_ready = max(1, int(readiness.get("trend_required_consecutive_ready", self.trend_recent_window)))
        self.require_temporal_stability = bool(readiness.get("require_temporal_stability", True))
        self.scorecard_min_samples = max(1, int(readiness.get("scorecard_min_samples", 10)))
        self.scorecard_recent_window = max(1, int(readiness.get("scorecard_recent_window", 5)))
        self.scorecard_min_pass_ratio = min(1.0, max(0.0, float(readiness.get("scorecard_min_pass_ratio", 1.0))))
        self.timeline_max_events = max(1, int(readiness.get("timeline_max_events", 200)))
        self.require_websocket_timing_validation = bool(readiness.get("require_websocket_timing_validation", True))
        self.websocket_timing_report_path = Path(readiness.get("websocket_timing_report_path", "PC_ENGINE/data/radar/websocket_timing_validation.json"))
        self.capability_evidence_path = Path(readiness.get("capability_evidence_path", "PC_ENGINE/data/radar/capability_evidence.jsonl"))
        self.max_capability_evidence_age_seconds = max(60, int(readiness.get("max_capability_evidence_age_seconds", 900)))

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

    def _live_credentials_ok(self, engine, target_mode: str | None = None) -> tuple[bool, str]:
        effective_mode = str(target_mode or engine.mode).upper()
        if effective_mode != "REAL":
            return True, "not required while target mode is PAPER"
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

    @staticmethod
    def _recovery_state_health(engine) -> tuple[bool, str]:
        """Require durable recovery state to cover every currently open position."""
        positions = getattr(getattr(engine, "state", None), "open_positions", {}) or {}
        if not positions:
            return True, "no open positions require recovery state"
        recovery = getattr(engine, "recovery", None)
        state_path = getattr(recovery, "state_path", None)
        if state_path is None:
            return False, "recovery state path unavailable"
        path = Path(state_path)
        if not path.is_file():
            return False, "persisted recovery state missing"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return False, f"persisted recovery state unreadable: {type(exc).__name__}"
        if not isinstance(payload, dict) or not isinstance(payload.get("positions"), dict):
            return False, "persisted recovery positions invalid"
        persisted = payload["positions"]
        missing = sorted(str(symbol) for symbol in positions if symbol not in persisted)
        if missing:
            return False, "open positions absent from recovery state: " + ",".join(missing)
        return True, f"persisted recovery covers {len(positions)} open positions"

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

    def trend(self) -> dict:
        rows = self._read_jsonl(self.history_path)
        engine = ReadinessTrendEngine(
            min_samples=self.trend_min_samples,
            recent_window=self.trend_recent_window,
            min_span_seconds=self.trend_min_span_seconds,
            degradation_threshold=self.trend_degradation_threshold,
            recovery_threshold=self.trend_recovery_threshold,
        )
        result = engine.analyze(rows).to_dict()
        result["history_path"] = str(self.history_path)
        result["history_enabled"] = self.history_enabled
        result["paper_only"] = True
        result["required_consecutive_ready"] = self.trend_required_consecutive_ready
        result["temporal_stability_required"] = self.require_temporal_stability
        return result

    def scorecard(self) -> dict:
        rows = self._read_jsonl(self.history_path)
        result = ReadinessStabilityScorecard(
            min_samples=self.scorecard_min_samples,
            recent_window=self.scorecard_recent_window,
            min_pass_ratio=self.scorecard_min_pass_ratio,
        ).analyze(rows).to_dict()
        result["history_path"] = str(self.history_path)
        result["history_enabled"] = self.history_enabled
        result["min_samples"] = self.scorecard_min_samples
        result["configured_recent_window"] = self.scorecard_recent_window
        result["min_pass_ratio"] = self.scorecard_min_pass_ratio
        return result

    def timeline(self, component=None, direction=None, from_status=None, to_status=None, limit=None) -> dict:
        rows = self._read_jsonl(self.history_path)
        return ReadinessDiagnosticTimeline(max_events=self.timeline_max_events).query(rows, component=component, direction=direction, from_status=from_status, to_status=to_status, limit=limit)

    def _evidence_quality(self, records: list, now_ms: int) -> tuple[bool, str, dict]:
        eligible = [record for record in records if bool(record.eligible)]
        ordered = sorted(records, key=lambda record: record.created_at_ms)
        eligible_ordered = sorted(eligible, key=lambda record: record.created_at_ms)
        symbols = {str(record.symbol) for record in eligible if str(record.symbol)}
        regimes = {str(record.regime) for record in eligible if str(record.regime)}
        if eligible_ordered:
            span_start = min(int(record.data_start_ms) for record in eligible_ordered)
            span_end = max(int(record.data_end_ms) for record in eligible_ordered)
            span_seconds = max(0.0, (span_end - span_start) / 1000.0)
        else:
            span_seconds = 0.0
        recent = ordered[-self.min_recent_evidence_records:]
        recent_ratio = (
            sum(bool(record.eligible) for record in recent) / len(recent)
            if recent else 0.0
        )
        economic_failures = []
        if self.require_positive_economic_ci:
            for record in eligible_ordered:
                durable = record.durable_outcome
                oos = record.chronological_oos
                if float(durable.lower_ci_bps) <= 0.0 or float(durable.bootstrap_lower_ci_bps) <= 0.0:
                    economic_failures.append(f"{record.candidate_id}@{record.version}:{record.symbol}:{record.regime}:durable_ci")
                if float(oos.bootstrap_lower_ci_bps) <= 0.0:
                    economic_failures.append(f"{record.candidate_id}@{record.version}:{record.symbol}:{record.regime}:oos_ci")
        stats = {
            "eligible_records": len(eligible_ordered),
            "required_eligible_records": self.min_eligible_evidence_records,
            "symbols": len(symbols),
            "required_symbols": self.min_evidence_symbols,
            "regimes": len(regimes),
            "required_regimes": self.min_evidence_regimes,
            "span_seconds": round(span_seconds, 3),
            "required_span_seconds": self.min_evidence_span_seconds,
            "recent_records": len(recent),
            "recent_eligible_ratio": round(recent_ratio, 6),
            "required_recent_eligible_ratio": self.min_recent_eligible_ratio,
            "economic_failures": economic_failures[:10],
        }
        blockers = []
        if len(eligible_ordered) < self.min_eligible_evidence_records:
            blockers.append("insufficient eligible evidence records")
        if len(symbols) < self.min_evidence_symbols:
            blockers.append("insufficient evidence symbol diversity")
        if len(regimes) < self.min_evidence_regimes:
            blockers.append("insufficient evidence regime diversity")
        if span_seconds < self.min_evidence_span_seconds:
            blockers.append("insufficient evidence time span")
        if len(recent) < self.min_recent_evidence_records:
            blockers.append("insufficient recent evidence history")
        if recent_ratio < self.min_recent_eligible_ratio:
            blockers.append("recent evidence eligibility degraded")
        if economic_failures:
            blockers.append("economic confidence interval gate failed")
        if not records:
            blockers.append("evidence ledger empty")
        detail = "; ".join(blockers) if blockers else "eligible PAPER evidence has breadth, duration, recent stability and positive net economics"
        return not blockers, detail, stats

    def collect(self, engine, persist_history: bool = True, target_mode: str | None = None) -> dict:
        now_ms = int(__import__('time').time() * 1000)
        states = self._read_jsonl(self.data_dir / "market_states.jsonl")
        outcomes = self._read_jsonl(self.data_dir / "state_outcomes.jsonl")
        state_fresh, state_fresh_detail = self._evidence_fresh(states, now_ms)
        outcome_fresh, outcome_fresh_detail = self._evidence_fresh(outcomes, now_ms)
        outcome_samples = sum(int(row.get("samples", 0) or 0) for row in outcomes)
        eligible = sum(bool(row.get("eligible")) for row in outcomes)
        eligible_outcome_samples = sum(
            int(row.get("samples", 0) or 0)
            for row in outcomes
            if bool(row.get("eligible"))
        )
        validation_dir = self.data_dir / "validation"
        preflight_ok = bool(engine.state.preflight.get("ok")) if engine.state.preflight else False
        watchdog_ok = bool(engine.state.watchdog.get("ok", False)) if engine.state.watchdog else False
        recovery_ok, recovery_detail = self._recovery_state_health(engine)
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

        credentials_ok, credentials_detail = self._live_credentials_ok(engine, target_mode=target_mode)
        evidence_quality_ok = False
        evidence_quality_detail = "evidence ledger unavailable"
        evidence_quality = {}
        try:
            ledger_path = engine.config.get("evidence", {}).get(
                "ledger_path", "PC_ENGINE/data/radar/evidence_ledger.jsonl"
            )
            ledger_records_for_gate = EvidenceLedger.load(ledger_path)
            evidence_quality_ok, evidence_quality_detail, evidence_quality = self._evidence_quality(
                ledger_records_for_gate, now_ms
            )
        except (OSError, ValueError, TypeError, KeyError) as exc:
            evidence_quality_detail = f"evidence ledger invalid: {exc}"
        target_is_real = str(target_mode or engine.mode).upper() == "REAL"
        enabled_venues = [
            str(name) for name, cfg in engine.config.get("exchanges", {}).items()
            if isinstance(cfg, dict) and bool(cfg.get("enabled", False))
        ]
        capabilities_ok = True
        capabilities_blockers: list[str] = []
        capability_evidence = {"path": str(self.capability_evidence_path), "applied": 0, "rejected": 0, "rejected_details": []}
        if target_is_real and self.require_verified_venue_capabilities:
            try:
                evidence_store = CapabilityEvidenceStore(self.capability_evidence_path)
                capability_evidence = self.venue_capabilities.apply_evidence(evidence_store, environment="REAL", max_age_seconds=self.max_capability_evidence_age_seconds, now_ms=now_ms)
            except (OSError, ValueError, TypeError):
                capabilities_blockers.append("capability evidence store unavailable")
            capabilities_ok, capabilities_blockers = self.venue_capabilities.verify_required(
                enabled_venues,
                build_real_execution_requirements(),
                "REAL",
            )
        capabilities_detail = (
            "verified REAL venue capabilities"
            if capabilities_ok
            else "unverified REAL venue capabilities: " + ",".join(capabilities_blockers)
        )
        report = self.gate.evaluate(
            mode=str(target_mode or engine.mode).upper(),
            preflight_ok=preflight_ok,
            state_samples=len(states),
            outcome_samples=outcome_samples,
            eligible_outcomes=eligible,
            eligible_outcome_samples=eligible_outcome_samples,
            evidence_quality_ok=evidence_quality_ok,
            evidence_quality_detail=evidence_quality_detail,
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
            capabilities_ok=capabilities_ok,
            capabilities_detail=capabilities_detail,
            account_reconciliation=engine.state.account_reconciliation or None,
            min_state_samples=self.min_state_samples,
            min_outcome_samples=self.min_outcome_samples,
            min_eligible_outcomes=self.min_eligible_outcomes,
            min_eligible_outcome_samples=self.min_eligible_outcome_samples,
        )
        payload = report.to_dict()
        timing_payload = self._read_json(self.websocket_timing_report_path)
        timing_fresh, timing_fresh_detail = self._validation_fresh(self.websocket_timing_report_path, now_ms)
        timing_eligible = bool(timing_payload.get("eligible_for_economic_interpretation", False))
        payload["venue_capabilities"] = {"required": self.require_verified_venue_capabilities, "enabled_venues": enabled_venues, "requirements": list(build_real_execution_requirements()), "blockers": capabilities_blockers, "snapshot": self.venue_capabilities.snapshot(), "evidence": capability_evidence}
        payload["websocket_timing"] = {
            "required": self.require_websocket_timing_validation,
            "eligible_for_economic_interpretation": timing_eligible,
            "fresh": timing_fresh,
            "fresh_detail": timing_fresh_detail,
            "path": str(self.websocket_timing_report_path),
        }
        if target_is_real and self.require_websocket_timing_validation and (not timing_eligible or not timing_fresh):
            payload["ready"] = False
            payload["status"] = "LOCKED"
            blockers = list(payload.get("blockers", []))
            blockers.append("websocket_timing_validation_required")
            payload["blockers"] = list(dict.fromkeys(blockers))
        payload["readiness_trend"] = self.trend()
        payload["readiness_scorecard"] = self.scorecard()
        payload["evidence"] = {
            "market_state_rows": len(states),
            "outcome_rows": len(outcomes),
            "outcome_samples": outcome_samples,
            "eligible_outcomes": eligible,
            "eligible_outcome_samples": eligible_outcome_samples,
            "evidence_quality": evidence_quality,
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
            "recovery_state_ok": recovery_ok,
            "recovery_state_detail": recovery_detail,
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
                readiness_trend=payload["readiness_trend"] if self.require_temporal_stability else {"status": "STABLE", "recent_ready_ratio": 1.0, "consecutive_ready": 1, "required_consecutive_ready": 1},
            )
        except (OSError, ValueError, TypeError):
            payload["paper_review"] = PaperReview.evaluate(
                payload, audit={}, learning={}, champion={},
                execution={
                    "ok": pending_orders_ok and execution_intents_ok and reconciliation_ok,
                    "detail": "paper execution state reconciled",
                },
                readiness_trend=payload["readiness_trend"] if self.require_temporal_stability else {"status": "STABLE", "recent_ready_ratio": 1.0, "consecutive_ready": 1, "required_consecutive_ready": 1},
            )
        if persist_history:
            self._persist_history(payload, now_ms)
        return payload
