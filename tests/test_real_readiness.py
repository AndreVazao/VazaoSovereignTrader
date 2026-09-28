from types import SimpleNamespace

from PC_ENGINE.core.real_readiness import RealReadinessGate


def test_gate_blocks_without_evidence():
    report = RealReadinessGate().evaluate(
        mode="PAPER", preflight_ok=True, state_samples=999,
        outcome_samples=0, eligible_outcomes=0,
        walk_forward_ok=True, regime_validation_ok=True,
        watchdog_ok=True, recovery_ok=True, execution_test_ok=True,
    )
    assert not report.ready
    assert report.status == "LOCKED"
    assert "MARKET_STATE_DATA" in report.blockers
    assert "STATE_OUTCOMES" in report.blockers


def test_gate_requires_all_checks():
    report = RealReadinessGate().evaluate(
        mode="PAPER", preflight_ok=True, state_samples=1000,
        outcome_samples=1000, eligible_outcomes=1,
        walk_forward_ok=True, regime_validation_ok=True,
        watchdog_ok=True, recovery_ok=True, execution_test_ok=True,
    )
    assert report.ready
    assert report.status == "READY_FOR_PROTECTED_REAL_REVIEW"


def test_real_mode_is_supported_but_does_not_authorize_execution():
    report = RealReadinessGate().evaluate(
        mode="REAL", preflight_ok=True, state_samples=1000,
        outcome_samples=1000, eligible_outcomes=1,
        walk_forward_ok=True, regime_validation_ok=True,
        watchdog_ok=True, recovery_ok=True, execution_test_ok=True,
    )
    assert report.ready
    assert report.status == "READY_FOR_PROTECTED_REAL_REVIEW"


def test_gate_blocks_financial_reconciliation_mismatch_even_if_legacy_flag_is_true():
    report = RealReadinessGate().evaluate(
        mode="REAL", preflight_ok=True, state_samples=1000,
        outcome_samples=1000, eligible_outcomes=1,
        walk_forward_ok=True, regime_validation_ok=True,
        watchdog_ok=True, recovery_ok=True, execution_test_ok=True,
        reconciliation_ok=True,
        account_reconciliation={"ok": False, "quote_mismatch": True},
    )
    assert not report.ready
    assert "PAPER_RECONCILIATION" in report.blockers


def test_gate_blocks_unresolved_execution_state():
    pending = RealReadinessGate().evaluate(
        mode="REAL", preflight_ok=True, state_samples=1000,
        outcome_samples=1000, eligible_outcomes=1,
        walk_forward_ok=True, regime_validation_ok=True,
        watchdog_ok=True, recovery_ok=True, execution_test_ok=True,
        pending_orders_ok=False,
    )
    assert not pending.ready
    assert "PENDING_ORDERS_CLEAR" in pending.blockers

    intent = RealReadinessGate().evaluate(
        mode="REAL", preflight_ok=True, state_samples=1000,
        outcome_samples=1000, eligible_outcomes=1,
        walk_forward_ok=True, recovery_ok=True,
        execution_test_ok=True, regime_validation_ok=True,
        watchdog_ok=True, execution_intents_ok=False,
    )
    assert not intent.ready
    assert "EXECUTION_INTENTS_CLEAR" in intent.blockers


def test_paper_review_distinguishes_missing_evidence_from_blockers():
    from PC_ENGINE.core.paper_review import PaperReview

    result = PaperReview.evaluate(
        {"ready": True, "status": "ok"},
        audit={"records": 0},
        learning={"degradation_detected": False},
        champion={"eligible": True},
        execution={"ok": True},
    )
    assert result["status"] == "INSUFFICIENT_EVIDENCE"
    assert result["insufficient"] == ("AUDIT",)
    assert result["blockers"] == ()


def test_paper_review_blocks_learning_degradation():
    from PC_ENGINE.core.paper_review import PaperReview

    result = PaperReview.evaluate(
        {"ready": True, "status": "ok"},
        audit={"records": 10},
        learning={"degradation_detected": True},
        champion={"eligible": True},
        execution={"ok": True},
    )
    assert result["status"] == "BLOCKED"
    assert "LEARNING" in result["blockers"]


def test_readiness_history_persists_and_limits_snapshots(tmp_path):
    from PC_ENGINE.core.real_readiness_service import RealReadinessService

    service = RealReadinessService({
        "real_readiness": {
            "history_enabled": True,
            "history_path": str(tmp_path / "history.jsonl"),
            "history_limit": 2,
        }
    })
    service._persist_history({"status": "LOCKED", "ready": False, "blockers": ["X"]}, 1)
    service._persist_history({"status": "LOCKED", "ready": False, "blockers": ["Y"]}, 2)
    service._persist_history({"status": "READY_FOR_PROTECTED_REAL_REVIEW", "ready": True, "blockers": [], "paper_review": {"status": "READY_FOR_REVIEW"}}, 3)
    history = service.history()
    assert history["records"] == 2
    assert history["ready_count"] == 1
    assert history["latest"]["timestamp_ms"] == 3


def test_readiness_service_exposes_trend_from_persisted_history(tmp_path):
    from PC_ENGINE.core.real_readiness_service import RealReadinessService

    service = RealReadinessService({
        "real_readiness": {
            "history_enabled": True,
            "history_path": str(tmp_path / "history.jsonl"),
            "history_limit": 20,
            "trend_min_samples": 5,
            "trend_recent_window": 2,
            "trend_min_span_seconds": 1,
            "trend_degradation_threshold": 0.20,
            "trend_recovery_threshold": 0.20,
        }
    })
    for index, ready in enumerate([True, True, True, False, False]):
        service._persist_history(
            {"status": "READY_FOR_PROTECTED_REAL_REVIEW" if ready else "LOCKED", "ready": ready, "blockers": [] if ready else ["X"]},
            1_000_000 + index * 1_000,
        )
    trend = service.trend()
    assert trend["status"] == "DEGRADING"
    assert trend["paper_only"] is True
    assert trend["history_path"].endswith("history.jsonl")


def test_paper_review_requires_stable_temporal_readiness():
    from PC_ENGINE.core.paper_review import PaperReview

    common = {
        "audit": {"records": 10},
        "learning": {"degradation_detected": False},
        "champion": {"eligible": True},
        "execution": {"ok": True},
    }
    degraded = PaperReview.evaluate(
        {"ready": True, "status": "ok"},
        readiness_trend={
            "status": "DEGRADING",
            "recent_ready_ratio": 0.0,
            "consecutive_ready": 0,
            "required_consecutive_ready": 3,
        },
        **common,
    )
    assert degraded["status"] == "BLOCKED"
    assert "READINESS_TREND" in degraded["blockers"]

    stable = PaperReview.evaluate(
        {"ready": True, "status": "ok"},
        readiness_trend={
            "status": "STABLE",
            "recent_ready_ratio": 1.0,
            "consecutive_ready": 3,
            "required_consecutive_ready": 3,
        },
        **common,
    )
    assert stable["status"] == "READY_FOR_REVIEW"
    assert "READINESS_TREND" not in stable["blockers"]


def test_paper_review_marks_temporal_history_insufficient():
    from PC_ENGINE.core.paper_review import PaperReview

    result = PaperReview.evaluate(
        {"ready": True, "status": "ok"},
        audit={"records": 10},
        learning={"degradation_detected": False},
        champion={"eligible": True},
        execution={"ok": True},
        readiness_trend={
            "status": "INSUFFICIENT_HISTORY",
            "reason": "minimum history samples not reached",
        },
    )
    assert result["status"] == "INSUFFICIENT_EVIDENCE"
    assert "READINESS_TREND" in result["insufficient"]


def test_readiness_service_exposes_diagnostic_timeline(tmp_path):
    from PC_ENGINE.core.real_readiness_service import RealReadinessService
    from PC_ENGINE.core.readiness_timeline import ReadinessDiagnosticTimeline

    service = RealReadinessService({
        "real_readiness": {
            "history_enabled": True,
            "history_path": str(tmp_path / "history.jsonl"),
            "history_limit": 20,
            "timeline_max_events": 20,
        }
    })
    names = ReadinessDiagnosticTimeline.COMPONENTS
    for index, state in enumerate(["PASS", "PASS", "BLOCKED", "PASS"]):
        service._persist_history(
            {
                "status": "READY_FOR_PROTECTED_REAL_REVIEW" if state == "PASS" else "LOCKED",
                "ready": state == "PASS",
                "blockers": [] if state == "PASS" else ["AUDIT"],
                "paper_review": {
                    "items": [
                        {"name": name, "status": state, "detail": "state change"}
                        for name in names
                    ]
                },
            },
            1_000_000 + index * 1_000,
        )

    timeline = service.timeline(component="AUDIT")
    assert timeline["paper_only"] is True
    assert timeline["returned_events"] == 2
    assert timeline["events"][0]["direction"] == "DEGRADING"
    assert timeline["events"][1]["direction"] == "RECOVERING"


def test_gate_requires_eligible_outcome_samples_when_supplied():
    report = RealReadinessGate().evaluate(
        mode="PAPER", preflight_ok=True, state_samples=1000,
        outcome_samples=1000, eligible_outcomes=1,
        eligible_outcome_samples=299,
        evidence_quality_ok=True,
        walk_forward_ok=True, regime_validation_ok=True,
        watchdog_ok=True, recovery_ok=True, execution_test_ok=True,
    )
    assert not report.ready
    assert "ELIGIBLE_OUTCOME_SAMPLES" in report.blockers


def test_evidence_quality_requires_breadth_duration_and_positive_economics(tmp_path):
    from PC_ENGINE.core.real_readiness_service import RealReadinessService

    service = RealReadinessService({
        "real_readiness": {
            "min_eligible_evidence_records": 3,
            "min_evidence_symbols": 2,
            "min_evidence_regimes": 2,
            "min_evidence_span_seconds": 3600,
            "min_recent_evidence_records": 3,
            "min_recent_eligible_ratio": 1.0,
            "require_positive_economic_ci": True,
        }
    })

    def record(symbol, regime, created, eligible=True):
        plane = SimpleNamespace(
            lower_ci_bps=1.0,
            bootstrap_lower_ci_bps=1.0,
        )
        oos = SimpleNamespace(
            bootstrap_lower_ci_bps=1.0,
        )
        return SimpleNamespace(
            eligible=eligible,
            symbol=symbol,
            regime=regime,
            created_at_ms=created,
            data_start_ms=created - 3_600_000,
            data_end_ms=created,
            candidate_id="candidate",
            version="1",
            durable_outcome=plane,
            chronological_oos=oos,
        )

    rows = [
        record("BTC/USDT", "TREND", 4_000_000),
        record("ETH/USDT", "TREND", 4_001_000),
        record("BTC/USDT", "MEAN_REVERSION", 4_002_000),
    ]
    ok, detail, stats = service._evidence_quality(rows, 4_003_000)
    assert ok
    assert detail.startswith("eligible PAPER evidence")
    assert stats["eligible_records"] == 3


def test_evidence_quality_blocks_negative_oos_confidence(tmp_path):
    from PC_ENGINE.core.real_readiness_service import RealReadinessService

    service = RealReadinessService({
        "real_readiness": {
            "min_eligible_evidence_records": 1,
            "min_evidence_symbols": 1,
            "min_evidence_regimes": 1,
            "min_evidence_span_seconds": 0,
            "min_recent_evidence_records": 1,
            "min_recent_eligible_ratio": 1.0,
            "require_positive_economic_ci": True,
        }
    })
    plane = SimpleNamespace(lower_ci_bps=1.0, bootstrap_lower_ci_bps=1.0)
    bad_oos = SimpleNamespace(bootstrap_lower_ci_bps=-0.1)
    row = SimpleNamespace(
        eligible=True, symbol="BTC/USDT", regime="TREND",
        created_at_ms=2_000_000, data_start_ms=2_000_000, data_end_ms=2_000_000,
        candidate_id="candidate", version="1",
        durable_outcome=plane, chronological_oos=bad_oos,
    )
    ok, detail, stats = service._evidence_quality([row], 2_001_000)
    assert not ok
    assert "economic confidence interval gate failed" in detail
    assert stats["economic_failures"]
