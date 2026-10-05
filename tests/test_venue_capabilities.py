from PC_ENGINE.core.capability_evidence_store import CapabilityEvidenceStore
from PC_ENGINE.core.runtime_capability_probe import RuntimeProbeResult
from PC_ENGINE.core.venue_capabilities import VenueCapability, VenueCapabilityRegistry, build_real_execution_requirements


def test_declared_capability_is_not_executable_until_verified():
    registry = VenueCapabilityRegistry({
        "TEST": {"real_order_submit": {"declared": True, "verified": False, "environment": "REAL"}}
    })
    ok, blockers = registry.verify_required(["TEST"], ["real_order_submit"], "REAL")
    assert not ok
    assert blockers == ["TEST:real_order_submit:not_verified"]


def test_verified_capability_requires_matching_environment():
    registry = VenueCapabilityRegistry()
    registry.register(VenueCapability(
        venue="TEST", capability="real_order_submit", declared=True, verified=True, environment="PAPER",
    ))
    ok, blockers = registry.verify_required(["TEST"], ["real_order_submit"], "REAL")
    assert not ok
    assert blockers == ["TEST:real_order_submit:missing"]


def test_real_requirements_are_explicit_and_serializable():
    requirements = build_real_execution_requirements()
    assert "real_order_submit" in requirements
    assert "real_order_cancel" in requirements
    assert "market_data_realtime" in requirements


def test_fresh_persisted_evidence_promotes_declared_capability(tmp_path):
    store = CapabilityEvidenceStore(tmp_path / "capabilities.jsonl")
    store.record(RuntimeProbeResult(
        venue="TEST", capability="market_data_realtime", environment="REAL",
        verified=True, evidence="runtime_probe:success:dict", risk_level="low",
    ), observed_at_ms=100_000)
    registry = VenueCapabilityRegistry({
        "TEST": {"market_data_realtime": {"declared": True, "verified": False, "environment": "REAL"}}
    })
    result = registry.apply_evidence(store, environment="REAL", max_age_seconds=60, now_ms=101_000)
    assert result["applied"] == 1
    row = registry.get("TEST", "market_data_realtime", "REAL")
    assert row is not None
    assert row.verified
    assert row.last_verified == "100000"
    assert row.evidence == "runtime_probe:success:dict"


def test_stale_evidence_does_not_promote_capability(tmp_path):
    store = CapabilityEvidenceStore(tmp_path / "capabilities.jsonl")
    store.record(RuntimeProbeResult(
        venue="TEST", capability="market_data_realtime", environment="REAL",
        verified=True, evidence="runtime_probe:success:dict", risk_level="low",
    ), observed_at_ms=1_000)
    registry = VenueCapabilityRegistry({
        "TEST": {"market_data_realtime": {"declared": True, "verified": False, "environment": "REAL"}}
    })
    result = registry.apply_evidence(store, environment="REAL", max_age_seconds=60, now_ms=62_000)
    assert result["applied"] == 0
    assert result["rejected"] == 1
    assert not registry.get("TEST", "market_data_realtime", "REAL").verified


def test_environment_mismatch_cannot_promote_evidence(tmp_path):
    store = CapabilityEvidenceStore(tmp_path / "capabilities.jsonl")
    store.record(RuntimeProbeResult(
        venue="TEST", capability="market_data_realtime", environment="PAPER",
        verified=True, evidence="runtime_probe:success:dict", risk_level="low",
    ), observed_at_ms=100_000)
    registry = VenueCapabilityRegistry({
        "TEST": {"market_data_realtime": {"declared": True, "verified": False, "environment": "REAL"}}
    })
    result = registry.apply_evidence(store, environment="REAL", max_age_seconds=60, now_ms=101_000)
    assert result["applied"] == 0
    assert registry.get("TEST", "market_data_realtime", "REAL").verified is False
