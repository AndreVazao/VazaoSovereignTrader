from __future__ import annotations

import pytest

from MOBILE_APP.office_snapshot import summarize_office_snapshot


def valid_snapshot():
    return {
        "ok": True, "schema_version": 1, "source": "vst_backend",
        "generated_at": "2026-11-12T15:00:00+00:00",
        "engine": {"status": "STOPPED", "mode": "PAPER", "running": False},
        "market_data": {"status": "STALE", "ok": True, "stale": True},
        "risk": {"status": "BLOCKED"},
        "safety": {"paper_only": True, "allow_real": False, "auto_promote_real": False},
        "verified_tasks": [],
    }


def test_mobile_snapshot_summary_keeps_stale_feed_unconfirmed():
    result = summarize_office_snapshot(valid_snapshot())
    assert result["engine_status"] == "STOPPED"
    assert result["mode"] == "PAPER"
    assert result["market_ok"] is False
    assert result["paper_only"] is True
    assert result["verified_task_count"] == 0


@pytest.mark.parametrize("payload", [None, [], {}, {"ok": False}, {"ok": True, "schema_version": 2}])
def test_mobile_snapshot_rejects_invalid_payload(payload):
    with pytest.raises(ValueError):
        summarize_office_snapshot(payload)


def test_mobile_snapshot_rejects_unverified_task_shape():
    payload = valid_snapshot()
    payload["verified_tasks"] = {}
    with pytest.raises(ValueError, match="snapshot_tasks_invalid"):
        summarize_office_snapshot(payload)
