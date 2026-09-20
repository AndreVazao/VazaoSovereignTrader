from __future__ import annotations

import json
import re
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlparse


@dataclass
class ResearchRequest:
    request_id: str
    message: str
    urls: list[str]
    status: str
    created_at: float
    updated_at: float
    result: str = ""


class TraderResearchInbox:
    """Human-to-brain research queue.

    This is deliberately only a research intake/control plane. A submitted idea
    never becomes a trading rule or live order by itself. A future research
    worker consumes PENDING items, gathers permitted public information, creates
    hypotheses and sends them through the existing validation/PAPER/OOS gates.
    """

    def __init__(self, data_dir: str = "PC_ENGINE/data/research"):
        self.root = Path(data_dir)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "requests.jsonl"

    def submit(self, message: str) -> ResearchRequest:
        message = str(message or "").strip()
        if not message:
            raise ValueError("research_message_required")
        item = ResearchRequest(
            request_id=uuid.uuid4().hex,
            message=message,
            urls=self._extract_urls(message),
            status="PENDING",
            created_at=time.time(),
            updated_at=time.time(),
        )
        self._append(item)
        return item

    def snapshot(self) -> dict:
        latest = self._latest()
        items = [asdict(x) for x in latest.values()]
        items.sort(key=lambda x: x["created_at"], reverse=True)
        return {
            "pending": sum(x["status"] == "PENDING" for x in items),
            "active": sum(x["status"] == "IN_PROGRESS" for x in items),
            "completed": sum(x["status"] == "COMPLETED" for x in items),
            "discarded": sum(x["status"] == "DISCARDED" for x in items),
            "requests": items[:30],
        }

    def _extract_urls(self, message: str) -> list[str]:
        found = re.findall(r'https?://[^\s<>"]+', message)
        urls = []
        for raw in found:
            url = raw.rstrip(".,;:)]}")
            parsed = urlparse(url)
            if parsed.scheme in {"http", "https"} and parsed.netloc and url not in urls:
                urls.append(url)
        return urls[:10]

    def _append(self, item: ResearchRequest) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(item), ensure_ascii=False) + "\n")

    def _latest(self) -> dict[str, ResearchRequest]:
        latest = {}
        if not self.path.exists():
            return latest
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    item = ResearchRequest(**json.loads(line))
                    latest[item.request_id] = item
                except (TypeError, ValueError):
                    continue
        return latest
