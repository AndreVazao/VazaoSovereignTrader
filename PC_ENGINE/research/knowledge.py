from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Iterable


class ResearchKnowledge:
    """Durable structured memory for research findings and failed hypotheses."""

    CATEGORIES = {
        "market_pattern", "lead_lag", "microstructure", "execution",
        "liquidity", "volatility", "regime", "venue_behaviour",
        "strategy", "risk", "failed_hypothesis",
    }

    def __init__(self, data_dir: str):
        self.root = Path(data_dir)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "knowledge.jsonl"

    def record(self, *, title: str, category: str, status: str,
               evidence: str, source_urls: Iterable[str] = (),
               metrics: dict | None = None, tags: Iterable[str] = (),
               hypothesis_id: str | None = None) -> dict:
        category = category if category in self.CATEGORIES else "market_pattern"
        row = {
            "knowledge_id": uuid.uuid4().hex,
            "hypothesis_id": hypothesis_id,
            "title": title.strip(),
            "category": category,
            "status": status,
            "evidence": evidence.strip(),
            "source_urls": list(source_urls),
            "metrics": metrics or {},
            "tags": list(tags),
            "created_at": time.time(),
        }
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        return row

    def search(self, text: str = "", category: str | None = None) -> list[dict]:
        needle = text.lower().strip()
        rows = []
        if not self.path.exists():
            return rows
        for line in self.path.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if category and row.get("category") != category:
                continue
            haystack = json.dumps(row, ensure_ascii=False).lower()
            if needle and needle not in haystack:
                continue
            rows.append(row)
        return rows

    def snapshot(self) -> dict:
        rows = self.search()
        return {
            "count": len(rows),
            "by_status": {s: sum(r.get("status") == s for r in rows)
                          for s in ("hypothesis", "validating", "paper", "accepted", "failed", "discarded")},
            "by_category": {c: sum(r.get("category") == c for r in rows) for c in sorted(self.CATEGORIES)},
            "recent": rows[-10:],
        }
