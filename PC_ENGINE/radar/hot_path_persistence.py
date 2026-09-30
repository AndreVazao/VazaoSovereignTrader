# Path: PC_ENGINE/radar/hot_path_persistence.py
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterable


def _repair_incomplete_tail(path: Path) -> None:
    """Remove only an unterminated final JSONL record before appending."""
    if not path.exists() or path.stat().st_size == 0:
        return
    with path.open("r+b") as handle:
        handle.seek(0, os.SEEK_END)
        end = handle.tell()
        handle.seek(-1, os.SEEK_END)
        if handle.read(1) == b"\n":
            return
        position = end
        chunk_size = 8192
        while position > 0:
            size = min(chunk_size, position)
            position -= size
            handle.seek(position)
            chunk = handle.read(size)
            newline = chunk.rfind(b"\n")
            if newline >= 0:
                handle.truncate(position + newline + 1)
                handle.flush()
                os.fsync(handle.fileno())
                return
        handle.truncate(0)
        handle.flush()
        os.fsync(handle.fileno())


def append_paper_outcomes(path: str | Path, outcomes: Iterable[dict[str, Any]]) -> int:
    """Durably append valid observation-only outcomes, repairing a torn final line first."""
    destination = Path(path)
    rows = list(outcomes)
    safe_rows = [
        row for row in rows
        if isinstance(row, dict)
        and row.get("paper_only") is True
        and row.get("orders_submitted") is False
        and row.get("status") == "COMPLETED"
    ]
    if not safe_rows:
        return 0
    # Serialize the complete batch before touching the file; invalid numeric values
    # must not leave a partial batch behind.
    payload = b"".join(
        (json.dumps(row, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
        for row in safe_rows
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    _repair_incomplete_tail(destination)
    with destination.open("ab") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    return len(safe_rows)
