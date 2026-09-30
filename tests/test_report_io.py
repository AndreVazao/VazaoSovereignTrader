from __future__ import annotations

import json
import pytest
from PC_ENGINE.radar import report_io


def test_atomic_write_json_replaces_complete_document(tmp_path):
    destination = tmp_path / "nested" / "report.json"
    report_io.atomic_write_json(destination, {"paper_only": True, "value": 7})
    assert json.loads(destination.read_text(encoding="utf-8")) == {"paper_only": True, "value": 7}
    assert list(destination.parent.glob("*.tmp")) == []


def test_atomic_write_json_preserves_previous_report_when_replace_fails(tmp_path, monkeypatch):
    destination = tmp_path / "report.json"
    destination.write_text('{"previous":true}', encoding="utf-8")
    def fail_replace(source, target):
        raise OSError("simulated disk/replace failure")
    monkeypatch.setattr(report_io.os, "replace", fail_replace)
    with pytest.raises(OSError, match="simulated"):
        report_io.atomic_write_json(destination, {"new": True})
    assert destination.read_text(encoding="utf-8") == '{"previous":true}'
    assert list(tmp_path.glob("*.tmp")) == []
