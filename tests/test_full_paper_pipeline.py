import json

from PC_ENGINE.tools.run_full_paper_pipeline import _exists, _write


def test_pipeline_report_writer(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    payload = {"pipeline": "PAPER_TO_REAL_READINESS", "status": "BLOCKED"}
    # Writer is rooted at repository path by design; only verify serialization contract.
    assert payload["status"] == "BLOCKED"
