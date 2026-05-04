from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List

from PC_ENGINE.core.config import LOG_DIR


class Ledger:
    def __init__(self, path: Path | None = None):
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        self.path = path or (LOG_DIR / "trades.jsonl")
        self.events_path = LOG_DIR / "events.jsonl"

    def event(self, event: str, data: Dict[str, Any]) -> None:
        row = {"ts": int(time.time()), "event": event, "data": data}
        with self.events_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def trade(self, record: Dict[str, Any]) -> None:
        row = {"ts": int(time.time()), **record}
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def recent_events(self, limit: int = 50) -> List[str]:
        if not self.events_path.exists():
            return []
        lines = self.events_path.read_text(encoding="utf-8").splitlines()[-limit:]
        out: List[str] = []
        for line in lines:
            try:
                row = json.loads(line)
                out.append(f"{row['ts']} {row['event']}: {row['data']}")
            except Exception:
                continue
        return out
