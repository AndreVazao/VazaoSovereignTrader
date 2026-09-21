from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List

from PC_ENGINE.core.config import LOG_DIR


class Ledger:
    def __init__(self, path: Path | None = None, events_path: Path | None = None, owner_id: str = "andre"):
        if path is None:
            private_dir = LOG_DIR.parent / "owners" / str(owner_id).strip().lower() / "logs"
            private_dir.mkdir(parents=True, exist_ok=True)
            path = private_dir / "trades.jsonl"
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.events_path = events_path or self.path.with_name("events.jsonl")
        self.events_path.parent.mkdir(parents=True, exist_ok=True)

    def event(self, event: str, data: Dict[str, Any]) -> None:
        row = {"ts": int(time.time()), "event": event, "data": data}
        with self.events_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def trade(self, record: Dict[str, Any]) -> None:
        row = {"ts": int(time.time()), **record}
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def read_trades(self, limit: int | None = None) -> List[Dict[str, Any]]:
        if not self.path.exists():
            return []
        lines = self.path.read_text(encoding="utf-8").splitlines()
        if limit is not None:
            lines = lines[-limit:]
        trades: List[Dict[str, Any]] = []
        for line in lines:
            try:
                trades.append(json.loads(line))
            except Exception:
                continue
        return trades

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
