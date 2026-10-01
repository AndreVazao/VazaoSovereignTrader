from __future__ import annotations

import io
from pathlib import Path

import pytest

from PC_ENGINE.api.operator_exchange import OperatorExchange


def test_exchange_creates_inbox_and_outbox(tmp_path: Path):
    exchange = OperatorExchange(tmp_path / "exchange")
    assert (tmp_path / "exchange" / "INBOX").is_dir()
    assert (tmp_path / "exchange" / "OUTBOX").is_dir()


def test_mobile_upload_is_inbox_only_and_download_is_safe(tmp_path: Path):
    exchange = OperatorExchange(tmp_path / "exchange")
    result = exchange.save_upload("INBOX", "../report.json", io.BytesIO(b'{"ok":true}'))
    assert result["folder"] == "INBOX"
    assert (tmp_path / "exchange" / "INBOX" / "report.json").read_text() == '{"ok":true}'
    assert exchange.resolve_download("INBOX", "report.json").name == "report.json"
    with pytest.raises(PermissionError):
        exchange.save_upload("OUTBOX", "bad.txt", io.BytesIO(b"x"))


def test_exchange_rejects_oversized_upload(tmp_path: Path):
    exchange = OperatorExchange(tmp_path / "exchange", max_upload_mb=1)
    with pytest.raises(ValueError):
        exchange.save_upload("INBOX", "large.bin", io.BytesIO(b"x" * (1024 * 1024 + 1)))
