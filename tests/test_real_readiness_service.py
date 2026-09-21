from pathlib import Path

from PC_ENGINE.core.real_readiness_service import RealReadinessService


def test_evidence_freshness_rejects_stale_rows():
    service = RealReadinessService({
        "real_readiness": {
            "max_evidence_age_seconds": 60,
            "max_validation_age_seconds": 300,
        }
    })
    ok, detail = service._evidence_fresh(
        [{"timestamp_ms": 1_000}],
        62_000,
    )
    assert not ok
    assert "age_ms=61000" in detail


def test_evidence_freshness_accepts_recent_rows():
    service = RealReadinessService({
        "real_readiness": {
            "max_evidence_age_seconds": 60,
            "max_validation_age_seconds": 300,
        }
    })
    ok, detail = service._evidence_fresh(
        [{"timestamp_ms": 59_000}],
        60_000,
    )
    assert ok
    assert "max_ms=60000" in detail


def test_validation_freshness_rejects_missing_artifact(tmp_path: Path):
    service = RealReadinessService({"real_readiness": {"max_validation_age_seconds": 300}})
    ok, detail = service._validation_fresh(tmp_path / "missing.json", 100_000)
    assert not ok
    assert detail == "artifact missing"
