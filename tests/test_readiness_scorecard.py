from PC_ENGINE.core.readiness_scorecard import ReadinessStabilityScorecard


def _rows(pattern, start=1_000_000, step=60_000):
    names = ("BASE", "AUDIT", "LEARNING", "CHAMPION", "EXECUTION", "READINESS_TREND")
    rows = []
    for i, state in enumerate(pattern):
        items = [
            {"name": name, "status": state, "detail": state.lower()}
            for name in names
        ]
        rows.append({
            "timestamp_ms": start + i * step,
            "ready": state == "PASS",
            "status": "READY" if state == "PASS" else "LOCKED",
            "blockers": [] if state == "PASS" else [name for name in names if state == "BLOCKED"],
            "paper_review": {"items": items},
        })
    return rows


def test_scorecard_detects_stable_component_set():
    result = ReadinessStabilityScorecard(min_samples=5, recent_window=3).analyze(_rows(["PASS"] * 6))
    assert result.status == "STABLE"
    assert result.to_dict()["paper_only"] is True
    assert len(result.components) == 6
    assert all(item.status == "PASS" for item in result.components)
    assert all(item.recent_pass_ratio == 1.0 for item in result.components)


def test_scorecard_identifies_current_blocker_and_streak():
    rows = _rows(["PASS"] * 5)
    rows[-1]["paper_review"]["items"][2] = {
        "name": "LEARNING", "status": "BLOCKED", "detail": "learning degradation"
    }
    result = ReadinessStabilityScorecard(min_samples=5, recent_window=3).analyze(rows)
    assert result.status == "BLOCKED"
    assert result.blockers == ("LEARNING",)
    learning = next(item for item in result.components if item.name == "LEARNING")
    assert learning.consecutive_blocked == 1
    assert learning.pass_ratio < 1.0


def test_scorecard_detects_recovery():
    rows = _rows(["BLOCKED", "BLOCKED", "BLOCKED", "PASS", "PASS", "PASS"])
    result = ReadinessStabilityScorecard(min_samples=5, recent_window=3, min_pass_ratio=1.0).analyze(rows)
    assert result.status == "STABLE"


def test_scorecard_requires_history():
    result = ReadinessStabilityScorecard(min_samples=5).analyze(_rows(["PASS"] * 4))
    assert result.status == "INSUFFICIENT_HISTORY"


def test_scorecard_fails_closed_on_malformed_review():
    rows = _rows(["PASS"] * 5)
    rows[2]["paper_review"]["items"][0]["status"] = "UNKNOWN"
    result = ReadinessStabilityScorecard(min_samples=5).analyze(rows)
    assert result.status == "INVALID_HISTORY"


def test_scorecard_rejects_duplicate_timestamps():
    rows = _rows(["PASS"] * 5)
    rows[3]["timestamp_ms"] = rows[2]["timestamp_ms"]
    result = ReadinessStabilityScorecard(min_samples=5).analyze(rows)
    assert result.status == "INVALID_HISTORY"


def test_scorecard_service_reads_persisted_history(tmp_path):
    from PC_ENGINE.core.real_readiness_service import RealReadinessService

    service = RealReadinessService({
        "real_readiness": {
            "history_enabled": True,
            "history_path": str(tmp_path / "history.jsonl"),
            "history_limit": 20,
            "scorecard_min_samples": 5,
            "scorecard_recent_window": 3,
        }
    })
    for i in range(5):
        service._persist_history(
            {
                "status": "READY_FOR_PROTECTED_REAL_REVIEW",
                "ready": True,
                "blockers": [],
                "paper_review": {
                    "items": [
                        {"name": name, "status": "PASS", "detail": "ok"}
                        for name in ReadinessStabilityScorecard.COMPONENTS
                    ]
                },
            },
            1_000_000 + i * 1_000,
        )
    scorecard = service.scorecard()
    assert scorecard["status"] == "STABLE"
    assert scorecard["paper_only"] is True
    assert scorecard["records"] == 5
