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
