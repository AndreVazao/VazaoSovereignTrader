from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class WebSocketTradeEventStore:
    """Bounded reader for the public WebSocket trade tape.

    The radar writes JSONL continuously. This reader intentionally loads only
    a bounded tail so the confluence loop does not re-read the whole tape on
    every evaluation.
    """

    def __init__(self, data_dir: str | Path = "PC_ENGINE/data/radar", max_tail_bytes: int = 2_000_000):
        self.path = Path(data_dir) / "websocket_events.jsonl"
        self.max_tail_bytes = max(64_000, int(max_tail_bytes))

    def recent(self, symbol: str, window_ms: int = 5_000, max_events: int = 500) -> list[dict[str, Any]]:
        if not self.path.exists() or max_events <= 0:
            return []
        try:
            with self.path.open("rb") as handle:
                handle.seek(0, 2)
                size = handle.tell()
                handle.seek(max(0, size - self.max_tail_bytes))
                raw = handle.read().decode("utf-8", errors="ignore")
        except OSError:
            return []

        now_candidates: list[int] = []
        parsed: list[dict[str, Any]] = []
        for line in raw.splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(row, dict) or str(row.get("symbol", "")) != symbol:
                continue
            try:
                ts = int(row.get("exchange_ts_ms") or row.get("local_ts_ms") or 0)
            except (TypeError, ValueError):
                continue
            if ts <= 0:
                continue
            row["_ts_ms"] = ts
            parsed.append(row)
            now_candidates.append(ts)

        if not parsed:
            return []
        reference_ts = max(now_candidates)
        cutoff = reference_ts - max(1, int(window_ms))
        result = [row for row in parsed if int(row.get("_ts_ms", 0)) >= cutoff]
        result.sort(key=lambda row: int(row.get("_ts_ms", 0)))
        result = result[-int(max_events):]
        for row in result:
            row.pop("_ts_ms", None)
        return result
