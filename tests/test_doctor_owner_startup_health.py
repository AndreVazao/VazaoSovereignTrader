from __future__ import annotations

import json
from pathlib import Path

from PC_ENGINE.tools.doctor import collect_diagnostics


def _ready_report() -> dict:
    return {
        "schema_version": 1,
        "status": "READY",
        "paper_only": True,
        "real_promotion_attempted": False,
        "critical_checks": [],
        "checks": {
            "startup_mode": {"ok": True, "configured": "PAPER", "effective": "PAPER"},
            "recovery_integrity": {"ok": True, "generation": 1, "primary_valid": True, "backup_valid": True},
        },
    }


def _write_config(root: Path, owner_id: str = "test-owner") -> None:
    config_dir = root / "PC_ENGINE" / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "config.example.json").write_text(
        json.dumps({"mode": "PAPER", "owner": {"id": owner_id}}),
        encoding="utf-8",
    )


def test_doctor_reads_owner_scoped_startup_health_written_by_engine(tmp_path: Path, monkeypatch):
    _write_config(tmp_path)
    monkeypatch.delenv("VST_OWNER_ID", raising=False)
    report_path = (
        tmp_path / "PC_ENGINE" / "data" / "owners" / "test-owner" / "startup" / "startup_health.json"
    )
    report_path.parent.mkdir(parents=True)
    report_path.write_text(json.dumps(_ready_report()), encoding="utf-8")

    result = collect_diagnostics(tmp_path)

    assert result["runtime_readiness"]["status"] == "STARTUP_CHECKS_PASSED"
    assert result["runtime_readiness"]["verified"] is True
    assert result["runtime_readiness"]["startup_health_report"] == str(report_path)


def test_doctor_does_not_read_another_owners_report_for_invalid_identity(tmp_path: Path, monkeypatch):
    _write_config(tmp_path, owner_id="andre")
    monkeypatch.setenv("VST_OWNER_ID", "../andre")
    other_owner_report = tmp_path / "PC_ENGINE" / "data" / "owners" / "andre" / "startup" / "startup_health.json"
    other_owner_report.parent.mkdir(parents=True)
    other_owner_report.write_text(json.dumps(_ready_report()), encoding="utf-8")

    result = collect_diagnostics(tmp_path)

    assert result["runtime_readiness"]["status"] == "UNKNOWN"
    assert result["runtime_readiness"]["verified"] is False
    assert "__invalid_owner_id__" in result["runtime_readiness"]["startup_health_report"]
