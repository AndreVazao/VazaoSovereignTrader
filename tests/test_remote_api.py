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

def test_evidence_learning_endpoint_returns_paper_guidance(tmp_path, monkeypatch):
    monkeypatch.setenv("VST_TEST_TOKEN", "secret-token")
    ledger_path = tmp_path / "evidence.jsonl"
    EvidenceLedger.append(ledger_path, _ledger_record(eligible=True))
    engine = FakeEngine()
    engine.config = {
        "real_mode_guard": {"enabled": True},
        "evidence": {"ledger_path": str(ledger_path)},
    }
    client = create_app(engine, token_env="VST_TEST_TOKEN").test_client()

    response = client.get("/evidence-learning", headers={"X-Token": "secret-token"})

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["paper_only"] is True
    assert payload["snapshot"]["records"] == 1
    assert payload["snapshot"]["actions"][0]["action"] == "OBSERVE"


def test_paper_autostart_policy_is_safe():
    from PC_ENGINE.main import _should_auto_start_paper

    assert _should_auto_start_paper({"engine": {"auto_start_paper": True}}, "PAPER")
    assert not _should_auto_start_paper({"engine": {"auto_start_paper": False}}, "PAPER")
    assert not _should_auto_start_paper({"engine": {"auto_start_paper": True}}, "REAL")
    assert not _should_auto_start_paper({}, "PAPER")



def test_autonomous_readiness_endpoint_is_read_only_preview(monkeypatch):
    monkeypatch.setenv("VST_TEST_TOKEN", "secret-token")
    import PC_ENGINE.api.server as server

    class FakeReadiness:
        def __init__(self, _config):
            self.called = False

        def collect(self, engine, *, persist_history=True, target_mode=None):
            assert persist_history is False
            assert target_mode == "REAL"
            assert engine.mode == "PAPER"
            self.called = True
            return {
                "ready": False,
                "status": "LOCKED",
                "blockers": ["EVIDENCE_QUALITY"],
                "paper_review": {"ready": False},
            }

    monkeypatch.setattr(server, "RealReadinessService", FakeReadiness)
    engine = FakeEngine()
    engine.config = {
        "real_mode_guard": {"enabled": True},
        "autonomous_execution": {
            "enabled": True,
            "allow_real": True,
            "auto_promote_real": True,
        },
    }
    client = create_app(engine, token_env="VST_TEST_TOKEN").test_client()

    response = client.get(
        "/autonomous-readiness",
        headers={"X-Token": "secret-token"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["target_mode"] == "REAL"
    assert payload["promotion_attempted"] is False
    assert payload["readiness"]["ready"] is False
    assert payload["readiness"]["blockers"] == ["EVIDENCE_QUALITY"]
    assert engine.mode == "PAPER"


def test_market_data_health_endpoint_reads_fresh_heartbeat(tmp_path, monkeypatch):
    monkeypatch.setenv("VST_TEST_TOKEN", "secret-token")
    import time
    health = tmp_path / "market_data_health.json"
    health.write_text(json.dumps({
        "service": "market_data_collector",
        "status": "RUNNING",
        "timestamp_ms": time.time_ns() // 1_000_000,
        "symbols": ["BTC/USDT"],
        "exchanges": ["binance"],
        "paper_only": True,
        "radar": {"events_total": 12, "events_by_exchange": {"binance": 12}},
    }), encoding="utf-8")
    engine = FakeEngine()
    engine.config = {"real_mode_guard": {"enabled": True}, "radar": {"data_dir": str(tmp_path)}}
    client = create_app(engine, token_env="VST_TEST_TOKEN").test_client()
    response = client.get("/market-data-health", headers={"X-Token": "secret-token"})
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["ok"] is True
    assert payload["stale"] is False
    assert payload["radar"]["events_total"] == 12


def test_market_data_health_endpoint_requires_token(monkeypatch):
    monkeypatch.setenv("VST_TEST_TOKEN", "secret-token")
    client = create_app(FakeEngine(), token_env="VST_TEST_TOKEN").test_client()
    assert client.get("/market-data-health").status_code == 401


def test_research_status_requires_auth(monkeypatch):
    monkeypatch.setenv("VST_TEST_TOKEN", "secret-token")
    client = create_app(FakeEngine(), token_env="VST_TEST_TOKEN").test_client()
    assert client.get("/research/status").status_code == 401


def test_research_status_is_paper_only(monkeypatch):
    monkeypatch.setenv("VST_TEST_TOKEN", "secret-token")
    client = create_app(FakeEngine(), token_env="VST_TEST_TOKEN").test_client()
    response = client.get("/research/status", headers={"X-Token": "secret-token"})
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert payload["paper_only"] is True


def test_operational_diagnostics_requires_token(monkeypatch):
    monkeypatch.setenv("VST_TEST_TOKEN", "secret-token")
    client = create_app(FakeEngine(), token_env="VST_TEST_TOKEN").test_client()
    assert client.get("/diagnostics").status_code == 401


def test_operational_diagnostics_aggregates_events_and_storage(tmp_path, monkeypatch):
    monkeypatch.setenv("VST_TEST_TOKEN", "secret-token")
    radar_dir = tmp_path / "radar"
    radar_dir.mkdir()
    (radar_dir / "websocket_events.jsonl").write_text(
        json.dumps({"exchange": "binance", "symbol": "BTC/USDT", "price": 100, "exchange_ts_ms": 1000, "local_ts_ms": 1100, "local_receive_latency_ms": 100}) + "\n"
        + json.dumps({"exchange": "binance", "symbol": "BTC/USDT", "price": 101, "exchange_ts_ms": 2000, "local_ts_ms": 2100, "local_receive_latency_ms": 100}) + "\n",
        encoding="utf-8",
    )
    engine = FakeEngine()
    engine.config = {"real_mode_guard": {"enabled": True}, "radar": {"data_dir": str(radar_dir)}}
    client = create_app(engine, token_env="VST_TEST_TOKEN").test_client()
    response = client.get("/diagnostics", headers={"X-Token": "secret-token"})
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["schema_version"] == 1
    assert payload["paper_only"] is True
    assert payload["market_data"]["latest_by_venue_symbol"]["binance"]["BTC/USDT"]["price"] == 101
    assert payload["storage"]["bytes"] > 0
    assert payload["diagnostics"]["orders_submitted"] is False


def test_operational_diagnostics_export_is_authenticated(monkeypatch):
    monkeypatch.setenv("VST_TEST_TOKEN", "secret-token")
    client = create_app(FakeEngine(), token_env="VST_TEST_TOKEN").test_client()
    response = client.get("/diagnostics/export", headers={"X-Token": "secret-token"})
    assert response.status_code == 200
    assert "attachment" in response.headers["Content-Disposition"]
    assert "vazao-operational-diagnostics.json" in response.headers["Content-Disposition"]



def test_market_data_health_resolves_relative_data_dir_from_repo_root(tmp_path, monkeypatch):
    import time
    from PC_ENGINE.diagnostics import path_utils

    monkeypatch.setenv("VST_TEST_TOKEN", "secret-token")
    monkeypatch.setattr(path_utils, "REPO_ROOT", tmp_path)
    data_dir = tmp_path / "runtime" / "radar"
    data_dir.mkdir(parents=True)
    (data_dir / "market_data_health.json").write_text(json.dumps({
        "service": "market_data_collector",
        "status": "RUNNING",
        "timestamp_ms": time.time_ns() // 1_000_000,
        "paper_only": True,
    }), encoding="utf-8")
    engine = FakeEngine()
    engine.config = {
        "real_mode_guard": {"enabled": True},
        "radar": {"data_dir": "runtime/radar"},
        "human_bridge": {"data_dir": str(tmp_path / "bridge")},
        "research": {"data_dir": str(tmp_path / "research")},
    }
    client = create_app(engine, token_env="VST_TEST_TOKEN").test_client()

    response = client.get("/market-data-health", headers={"X-Token": "secret-token"})

    assert response.status_code == 200
    assert response.get_json()["ok"] is True



def test_venue_economic_evidence_requires_authentication(monkeypatch):
    monkeypatch.setenv("VST_TEST_TOKEN", "secret-token")
    client = create_app(FakeEngine(), token_env="VST_TEST_TOKEN").test_client()
    assert client.get("/venue-economic-evidence").status_code == 401


def test_venue_economic_evidence_reads_configured_report_and_fails_closed(tmp_path, monkeypatch):
    from PC_ENGINE.diagnostics import path_utils

    monkeypatch.setenv("VST_TEST_TOKEN", "secret-token")
    monkeypatch.setattr(path_utils, "REPO_ROOT", tmp_path)
    report_path = tmp_path / "runtime" / "custom-economic.json"
    report_path.parent.mkdir(parents=True)
    report_path.write_text(json.dumps({
        "status": "OK",
        "venues": [{"venue": "coinbase", "status": "INSUFFICIENT_DATA"}],
        "paper_only": True,
        "orders_submitted": False,
        "execution_authorized": False,
    }), encoding="utf-8")

    engine = FakeEngine()
    engine.config = {
        "real_mode_guard": {"enabled": True},
        "radar": {
            "data_dir": "runtime/radar",
            "evidence_reports": {"venue_economic_evidence": "runtime/custom-economic.json"},
        },
        "human_bridge": {"data_dir": str(tmp_path / "bridge")},
        "research": {"data_dir": str(tmp_path / "research")},
    }
    client = create_app(engine, token_env="VST_TEST_TOKEN").test_client()

    response = client.get("/venue-economic-evidence", headers={"X-Token": "secret-token"})
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["venues"][0]["venue"] == "coinbase"
    assert payload["paper_only"] is True
    assert payload["orders_submitted"] is False
    assert payload["execution_authorized"] is False
    assert payload["report_path"] == str(report_path)

    report_path.write_text(json.dumps({
        "venues": [{"venue": "coinbase"}],
        "paper_only": True,
        "orders_submitted": False,
        "execution_authorized": True,
    }), encoding="utf-8")
    invalid = client.get("/venue-economic-evidence", headers={"X-Token": "secret-token"})
    assert invalid.status_code == 409
    assert invalid.get_json()["execution_authorized"] is False
