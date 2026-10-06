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


def test_recovery_health_requires_persisted_open_positions(tmp_path: Path):
    import json
    from types import SimpleNamespace

    service = RealReadinessService({"real_readiness": {"data_dir": str(tmp_path)}})
    state_path = tmp_path / "runtime_state.json"
    engine = SimpleNamespace(
        state=SimpleNamespace(open_positions={"BTC/USDT": object()}),
        recovery=SimpleNamespace(state_path=state_path),
    )
    ok, detail = service._recovery_state_health(engine)
    assert not ok
    assert "missing" in detail

    state_path.write_text(json.dumps({"positions": {}}), encoding="utf-8")
    ok, detail = service._recovery_state_health(engine)
    assert not ok
    assert "BTC/USDT" in detail

    state_path.write_text(json.dumps({"positions": {"BTC/USDT": {"symbol": "BTC/USDT"}}}), encoding="utf-8")
    ok, detail = service._recovery_state_health(engine)
    assert ok
    assert "covers 1 open positions" in detail


def test_recovery_health_allows_no_open_positions_without_state_file(tmp_path: Path):
    from types import SimpleNamespace

    service = RealReadinessService({"real_readiness": {"data_dir": str(tmp_path)}})
    engine = SimpleNamespace(
        state=SimpleNamespace(open_positions={}),
        recovery=SimpleNamespace(state_path=tmp_path / "missing.json"),
    )
    ok, detail = service._recovery_state_health(engine)
    assert ok
    assert "no open positions" in detail


def test_real_readiness_uses_fresh_persisted_capability_evidence(tmp_path):
    from PC_ENGINE.core.capability_evidence_store import CapabilityEvidenceStore
    from PC_ENGINE.core.runtime_capability_probe import RuntimeProbeResult
    from types import SimpleNamespace

    evidence_path = tmp_path / "capabilities.jsonl"
    store = CapabilityEvidenceStore(evidence_path)
    store.record(RuntimeProbeResult(
        venue="TEST", capability="market_data_realtime", environment="REAL",
        verified=True, evidence="runtime_probe:success:dict", risk_level="low",
    ), observed_at_ms=100_000)
    service = RealReadinessService({"real_readiness": {
        "require_verified_venue_capabilities": True,
        "capability_evidence_path": str(evidence_path),
        "max_capability_evidence_age_seconds": 60,
        "venue_capabilities": {"TEST": {"market_data_realtime": {
            "declared": True, "verified": False, "environment": "REAL"
        }}},
    }})
    applied = service.venue_capabilities.apply_evidence(store, environment="REAL", max_age_seconds=60, now_ms=101_000)
    assert applied["applied"] == 1
    assert service.venue_capabilities.get("TEST", "market_data_realtime", "REAL").verified


def test_real_readiness_capability_evidence_is_fail_closed_when_stale(tmp_path):
    from PC_ENGINE.core.capability_evidence_store import CapabilityEvidenceStore
    from PC_ENGINE.core.runtime_capability_probe import RuntimeProbeResult

    evidence_path = tmp_path / "capabilities.jsonl"
    store = CapabilityEvidenceStore(evidence_path)
    store.record(RuntimeProbeResult(
        venue="TEST", capability="market_data_realtime", environment="REAL",
        verified=True, evidence="runtime_probe:success:dict", risk_level="low",
    ), observed_at_ms=1_000)
    service = RealReadinessService({"real_readiness": {
        "capability_evidence_path": str(evidence_path),
        "venue_capabilities": {"TEST": {"market_data_realtime": {
            "declared": True, "verified": False, "environment": "REAL"
        }}},
    }})
    result = service.venue_capabilities.apply_evidence(store, environment="REAL", max_age_seconds=60, now_ms=62_000)
    assert result["applied"] == 0
    assert not service.venue_capabilities.get("TEST", "market_data_realtime", "REAL").verified
