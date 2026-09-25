from __future__ import annotations

import json

from PC_ENGINE.api.server import create_app
from PC_ENGINE.radar.evidence_ledger import EvidenceLedger, EvidenceLedgerRecord, EvidencePlaneSummary


class FakeEngine:
    owner_id = "andre"
    mode = "PAPER"
    config = {"real_mode_guard": {"enabled": True}}

    def snapshot(self):
        return {"status": "OFF", "mode": self.mode}

    def run_preflight(self):
        return {"ok": True, "errors": [], "warnings": []}

    def start(self):
        return None

    def pause(self, _paused=True):
        return None

    def stop(self):
        return None

    def set_mode(self, mode):
        self.mode = mode


def test_health_is_public():
    client = create_app(FakeEngine(), token_env="VST_TEST_TOKEN").test_client()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["ok"] is True


def test_status_requires_token(monkeypatch):
    monkeypatch.setenv("VST_TEST_TOKEN", "secret-token")
    client = create_app(FakeEngine(), token_env="VST_TEST_TOKEN").test_client()

    assert client.get("/status").status_code == 401
    assert client.get("/status", headers={"X-Token": "secret-token"}).status_code == 200

def _ledger_record(*, eligible: bool, source_digest: str = ""):
    durable = EvidencePlaneSummary("durable", "PASS", 4, 2, 2, 3.0, 1.0, 1.2, 1.0, 2)
    oos = EvidencePlaneSummary("chronological_oos", "PASS", 4, 2, 2, 2.5, 0.8, 1.0, 1.0, 2)
    record = EvidenceLedgerRecord(
        created_at_ms=1_700_000_000_000,
        candidate_id="candidate-a",
        version="v1",
        strategy="momentum",
        symbol="BTCUSDT",
        regime="TREND",
        horizon_ms=60_000,
        eligible=eligible,
        reason="eligible" if eligible else "insufficient_samples",
        reason_codes=() if eligible else ("insufficient_samples",),
        data_start_ms=1_699_000_000_000,
        data_end_ms=1_699_999_000_000,
        state_count=4,
        outcome_count=4,
        durable_outcome=durable,
        chronological_oos=oos,
        source_digest=source_digest,
    )
    return EvidenceLedger.with_digest(record)

def test_evidence_ledger_endpoint_reports_verified_records(tmp_path, monkeypatch):
    monkeypatch.setenv("VST_TEST_TOKEN", "secret-token")
    ledger_path = tmp_path / "evidence.jsonl"
    EvidenceLedger.append(ledger_path, _ledger_record(eligible=True))
    engine = FakeEngine()
    engine.config = {
        "real_mode_guard": {"enabled": True},
        "evidence": {"ledger_path": str(ledger_path)},
    }
    client = create_app(engine, token_env="VST_TEST_TOKEN").test_client()

    response = client.get(
        "/evidence-ledger?candidate_id=candidate-a&eligible=true",
        headers={"X-Token": "secret-token"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["summary"]["records"] == 1
    assert payload["summary"]["eligible_records"] == 1
    assert payload["records"][0]["candidate_id"] == "candidate-a"
    assert payload["filters"]["eligible"] is True


def test_evidence_ledger_endpoint_rejects_tampering(tmp_path, monkeypatch):
    monkeypatch.setenv("VST_TEST_TOKEN", "secret-token")
    ledger_path = tmp_path / "evidence.jsonl"
    EvidenceLedger.append(ledger_path, _ledger_record(eligible=True))
    ledger_path.write_text(ledger_path.read_text(encoding="utf-8").replace('"eligible":true', '"eligible":false'), encoding="utf-8")
    engine = FakeEngine()
    engine.config = {
        "real_mode_guard": {"enabled": True},
        "evidence": {"ledger_path": str(ledger_path)},
    }
    client = create_app(engine, token_env="VST_TEST_TOKEN").test_client()

    response = client.get("/evidence-ledger", headers={"X-Token": "secret-token"})

    assert response.status_code == 409
    assert response.get_json()["error"] == "evidence_ledger_invalid"


def test_evidence_ledger_endpoint_rejects_invalid_eligible_filter(monkeypatch):
    monkeypatch.setenv("VST_TEST_TOKEN", "secret-token")
    client = create_app(FakeEngine(), token_env="VST_TEST_TOKEN").test_client()

    response = client.get(
        "/evidence-ledger?eligible=maybe",
        headers={"X-Token": "secret-token"},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "eligible_must_be_boolean"

def test_evidence_ledger_audit_endpoint_reports_aggregate(tmp_path, monkeypatch):
    monkeypatch.setenv("VST_TEST_TOKEN", "secret-token")
    ledger_path = tmp_path / "evidence.jsonl"
    from PC_ENGINE.radar.evidence_ledger import EvidenceLedger, EvidenceLedgerRecord, EvidencePlaneSummary

    plane = EvidencePlaneSummary("durable", "PASS", 2, 1, 1, 2.0, 1.0, 1.0, 1.0, 1)
    oos = EvidencePlaneSummary("chronological_oos", "PASS", 2, 1, 1, 2.0, 1.0, 1.0, 1.0, 1)
    record = EvidenceLedgerRecord(
        created_at_ms=1_700_000_000_000,
        candidate_id="candidate-a",
        version="v1",
        strategy="momentum",
        symbol="BTCUSDT",
        regime="TREND",
        horizon_ms=60_000,
        eligible=True,
        reason="",
        reason_codes=(),
        data_start_ms=1_699_000_000_000,
        data_end_ms=1_699_999_000_000,
        state_count=2,
        outcome_count=2,
        durable_outcome=plane,
        chronological_oos=oos,
        source_digest="",
    )
    EvidenceLedger.append(ledger_path, record)

    engine = FakeEngine()
    engine.config = {
        "real_mode_guard": {"enabled": True},
        "evidence": {"ledger_path": str(ledger_path)},
    }
    client = create_app(engine, token_env="VST_TEST_TOKEN").test_client()
    response = client.get("/evidence-ledger/audit", headers={"X-Token": "secret-token"})

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["report"]["records"] == 1
    assert payload["report"]["eligible_records"] == 1
    assert payload["report"]["eligibility_ratio"] == 1.0
    assert payload["report"]["symbols"] == ["BTCUSDT"]


def test_evidence_ledger_audit_endpoint_rejects_tampering(tmp_path, monkeypatch):
    monkeypatch.setenv("VST_TEST_TOKEN", "secret-token")
    ledger_path = tmp_path / "evidence.jsonl"
    from PC_ENGINE.radar.evidence_ledger import EvidenceLedger, EvidenceLedgerRecord, EvidencePlaneSummary

    plane = EvidencePlaneSummary("durable", "PASS", 1, 1, 1, 1.0, 1.0, 1.0, 1.0, 1)
    record = EvidenceLedgerRecord(
        created_at_ms=1_700_000_000_000,
        candidate_id="candidate-a",
        version="v1",
        strategy="momentum",
        symbol="BTCUSDT",
        regime="TREND",
        horizon_ms=60_000,
        eligible=True,
        reason="",
        reason_codes=(),
        data_start_ms=1_699_000_000_000,
        data_end_ms=1_699_999_000_000,
        state_count=1,
        outcome_count=1,
        durable_outcome=plane,
        chronological_oos=plane,
        source_digest="",
    )
    saved = EvidenceLedger.append(ledger_path, record)
    payload = saved.to_dict()
    payload["eligible"] = False
    ledger_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    engine = FakeEngine()
    engine.config = {"real_mode_guard": {"enabled": True}, "evidence": {"ledger_path": str(ledger_path)}}
    client = create_app(engine, token_env="VST_TEST_TOKEN").test_client()
    response = client.get("/evidence-ledger/audit", headers={"X-Token": "secret-token"})

    assert response.status_code == 409
    assert response.get_json()["error"] == "evidence_ledger_invalid"
