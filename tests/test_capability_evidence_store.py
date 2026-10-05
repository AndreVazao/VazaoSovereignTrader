from PC_ENGINE.core.capability_evidence_store import CapabilityEvidenceStore
from PC_ENGINE.core.runtime_capability_probe import RuntimeProbeResult


def test_record_persists_runtime_probe_evidence(tmp_path):
    store = CapabilityEvidenceStore(tmp_path / "capabilities.jsonl")
    result = RuntimeProbeResult(
        venue="TEST",
        capability="market_data_realtime",
        environment="REAL",
        verified=True,
        evidence="runtime_probe:success:dict",
        risk_level="low",
    )

    row = store.record(result, observed_at_ms=123456789)

    assert row["schema_version"] == 1
    assert row["observed_at_ms"] == 123456789
    assert store.load() == [row]


def test_latest_returns_newest_matching_evidence(tmp_path):
    store = CapabilityEvidenceStore(tmp_path / "capabilities.jsonl")
    first = RuntimeProbeResult(
        venue="TEST",
        capability="account_balances",
        environment="REAL",
        verified=False,
        evidence="runtime_probe:error:TimeoutError:offline",
        risk_level="high",
    )
    second = RuntimeProbeResult(
        venue="TEST",
        capability="account_balances",
        environment="REAL",
        verified=True,
        evidence="runtime_probe:success:dict",
        risk_level="medium",
    )

    store.record(first, observed_at_ms=100)
    latest = store.record(second, observed_at_ms=200)

    assert store.latest(
        venue="TEST",
        capability="account_balances",
        environment="REAL",
    ) == latest


def test_latest_isolated_by_environment_and_capability(tmp_path):
    store = CapabilityEvidenceStore(tmp_path / "capabilities.jsonl")
    result = RuntimeProbeResult(
        venue="TEST",
        capability="market_data_realtime",
        environment="PAPER",
        verified=True,
        evidence="runtime_probe:success:dict",
        risk_level="low",
    )
    store.record(result, observed_at_ms=100)

    assert store.latest(
        venue="TEST",
        capability="market_data_realtime",
        environment="REAL",
    ) is None
    assert store.latest(
        venue="TEST",
        capability="account_balances",
        environment="PAPER",
    ) is None


def test_malformed_rows_are_ignored(tmp_path):
    path = tmp_path / "capabilities.jsonl"
    path.write_text(
        '{"schema_version":1,"venue":"TEST","capability":"market_data_realtime","environment":"PAPER","observed_at_ms":1}\n'
        'not-json\n'
        '{"schema_version":999,"venue":"TEST"}\n',
        encoding="utf-8",
    )

    assert len(CapabilityEvidenceStore(path).load()) == 1
