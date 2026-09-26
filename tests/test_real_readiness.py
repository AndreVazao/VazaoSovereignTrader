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
