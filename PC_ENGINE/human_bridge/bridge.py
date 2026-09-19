from __future__ import annotations

import json
import threading
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

@dataclass
class HumanInteractionRequest:
    request_id: str
    platform: str
    kind: str
    title: str
    message: str
    url: str | None
    screenshot_path: str | None
    fields: list[dict[str, Any]]
    status: str
    created_at: float
    updated_at: float

class HumanInteractionBridge:
    _RAM_RESPONSES: dict[str, dict[str, Any]] = {}
    _RAM_LOCK = threading.RLock()
    """Durable control-plane for human web interactions.

    Request metadata is persisted so PC/mobile can disconnect independently.
    Secrets are NEVER persisted; responses stay in RAM until consumed.
    """
    def __init__(self, data_dir: str = "PC_ENGINE/data/human_bridge"):
        self.root = Path(data_dir)
        self.root.mkdir(parents=True, exist_ok=True)
        self.requests_path = self.root / "requests.jsonl"
        self._lock = threading.RLock()

    def create_request(self, platform: str, kind: str, title: str, message: str, *, url: str | None = None, screenshot_path: str | None = None, fields: list[dict[str, Any]] | None = None) -> HumanInteractionRequest:
        now = time.time()
        item = HumanInteractionRequest(uuid.uuid4().hex, platform, kind, title, message, url, screenshot_path, fields or [], "PENDING", now, now)
        with self._lock:
            self._append(item)
        return item

    def pending(self) -> list[dict[str, Any]]:
        latest = self._latest()
        return [asdict(x) for x in latest.values() if x.status == "PENDING"]

    def respond(self, request_id: str, *, action: str, values: dict[str, Any] | None = None) -> bool:
        values = values or {}
        with self._lock:
            item = self._latest().get(request_id)
            if item is None or item.status != "PENDING":
                return False
            item.status = "RESPONDED"
            item.updated_at = time.time()
            self._append(item)
            # Sensitive values are intentionally RAM-only.
            with self._RAM_LOCK:
                self._RAM_RESPONSES[self._response_key(request_id)] = {"action": action, "values": values, "received_at": item.updated_at}
            return True

    def consume_response(self, request_id: str) -> dict[str, Any] | None:
        with self._RAM_LOCK:
            return self._RAM_RESPONSES.pop(self._response_key(request_id), None)

    def cancel(self, request_id: str) -> bool:
        with self._lock:
            item = self._latest().get(request_id)
            if item is None or item.status != "PENDING":
                return False
            item.status = "CANCELLED"
            item.updated_at = time.time()
            self._append(item)
            return True

    def snapshot(self) -> dict[str, Any]:
        latest = self._latest()
        return {"pending": sum(x.status == "PENDING" for x in latest.values()), "responded_waiting_pc": sum(1 for k in self._RAM_RESPONSES if k.startswith(str(self.root.resolve()) + ":")), "requests": [asdict(x) for x in latest.values() if x.status in {"PENDING", "RESPONDED"}]}

    def _response_key(self, request_id: str) -> str:
        return f"{self.root.resolve()}:{request_id}"

    def _append(self, item: HumanInteractionRequest) -> None:
        with self.requests_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(item), ensure_ascii=False) + "\\n")

    def _latest(self) -> dict[str, HumanInteractionRequest]:
        latest: dict[str, HumanInteractionRequest] = {}
        if not self.requests_path.exists():
            return latest
        with self.requests_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    item = HumanInteractionRequest(**json.loads(line))
                    latest[item.request_id] = item
                except (ValueError, TypeError):
                    continue
        return latest
