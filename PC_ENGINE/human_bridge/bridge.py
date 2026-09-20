from __future__ import annotations

import json
import threading
import hmac
import time
import uuid
import hashlib
import secrets
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
    session_id: str | None = None
    expires_at: float = 0.0
    claim_token_hash: str | None = None


class HumanInteractionBridge:
    _RAM_RESPONSES: dict[str, dict[str, Any]] = {}
    _RAM_LOCK = threading.RLock()
    _RAM_CLAIMS: dict[str, str] = {}

    """Durable control-plane for human web interactions.

    Request metadata is persisted so PC/mobile can disconnect independently.
    Secrets are NEVER persisted; responses stay in RAM until consumed.
    """

    def __init__(self, data_dir: str = "PC_ENGINE/data/human_bridge", default_ttl_seconds: int = 900):
        self.root = Path(data_dir)
        self.root.mkdir(parents=True, exist_ok=True)
        self.requests_path = self.root / "requests.jsonl"
        self.default_ttl_seconds = max(30, int(default_ttl_seconds))
        self._lock = threading.RLock()

    def create_request(
        self,
        platform: str,
        kind: str,
        title: str,
        message: str,
        *,
        url: str | None = None,
        screenshot_path: str | None = None,
        fields: list[dict[str, Any]] | None = None,
        session_id: str | None = None,
        ttl_seconds: int | None = None,
    ) -> HumanInteractionRequest:
        now = time.time()
        ttl = max(30, int(ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds))
        request_id = uuid.uuid4().hex
        claim_token = secrets.token_urlsafe(24)
        item = HumanInteractionRequest(
            request_id,
            platform,
            kind,
            title,
            message,
            url,
            screenshot_path,
            fields or [],
            "PENDING",
            now,
            now,
            session_id,
            now + ttl,
            hashlib.sha256(claim_token.encode()).hexdigest(),
        )
        with self._lock:
            self._append(item)
            with self._RAM_LOCK:
                self._RAM_CLAIMS[item.request_id] = claim_token
        return item

    def get(self, request_id: str) -> HumanInteractionRequest | None:
        with self._lock:
            return self._latest().get(request_id)

    def pending(self) -> list[dict[str, Any]]:
        self.expire_stale()
        latest = self._latest()
        return [self.public_item(x) for x in latest.values() if x.status == "PENDING"]

    def expire_stale(self) -> int:
        changed = 0
        with self._lock:
            latest = self._latest()
            now = time.time()
            for item in latest.values():
                if item.status in {"PENDING", "RESPONDED"} and item.expires_at and now >= item.expires_at:
                    item.status = "EXPIRED"
                    item.updated_at = now
                    self._append(item)
                    with self._RAM_LOCK:
                        self._RAM_RESPONSES.pop(self._response_key(item.request_id), None)
                        self._RAM_CLAIMS.pop(item.request_id, None)
                    changed += 1
        return changed

    def reissue_claim(self, request_id: str) -> str | None:
        self.expire_stale()
        with self._lock:
            item = self._latest().get(request_id)
            if item is None or item.status != "PENDING":
                return None
            token = secrets.token_urlsafe(24)
            item.claim_token_hash = hashlib.sha256(token.encode()).hexdigest()
            item.updated_at = time.time()
            self._append(item)
            with self._RAM_LOCK:
                self._RAM_CLAIMS[request_id] = token
            return token

    def claim_token(self, request_id: str) -> str | None:
        with self._RAM_LOCK:
            return self._RAM_CLAIMS.get(request_id)

    def authenticate_claim(self, request_id: str, claim_token: str) -> bool:
        item = self.get(request_id)
        if item is None or item.status != "PENDING" or not claim_token or not item.claim_token_hash:
            return False
        digest = hashlib.sha256(claim_token.encode()).hexdigest()
        return hmac.compare_digest(digest, item.claim_token_hash) and not self._is_expired(item)

    def public_item(self, item: HumanInteractionRequest) -> dict[str, Any]:
        data = asdict(item)
        data.pop("claim_token_hash", None)
        token = self.claim_token(item.request_id)
        if token and item.status == "PENDING":
            data["claim_token"] = token
        return data

    def respond(self, request_id: str, *, action: str, values: dict[str, Any] | None = None, claim_token: str = "") -> bool:
        values = values or {}
        if not self.authenticate_claim(request_id, claim_token):
            return False
        with self._lock:
            item = self._latest().get(request_id)
            if item is None or item.status != "PENDING" or self._is_expired(item):
                return False
            item.status = "RESPONDED"
            item.updated_at = time.time()
            self._append(item)
            with self._RAM_LOCK:
                self._RAM_RESPONSES[self._response_key(request_id)] = {
                    "action": action,
                    "values": values,
                    "received_at": item.updated_at,
                }
            return True

    def peek_response(self, request_id: str) -> dict[str, Any] | None:
        with self._RAM_LOCK:
            response = self._RAM_RESPONSES.get(self._response_key(request_id))
            return dict(response) if response is not None else None

    def mark_applied(self, request_id: str) -> bool:
        with self._lock:
            item = self._latest().get(request_id)
            if item is None or item.status != "RESPONDED":
                return False
            item.status = "APPLIED"
            item.updated_at = time.time()
            self._append(item)
            return True

    def mark_completed(self, request_id: str) -> bool:
        with self._lock:
            item = self._latest().get(request_id)
            if item is None or item.status != "APPLIED":
                return False
            item.status = "COMPLETED"
            item.updated_at = time.time()
            self._append(item)
            return True

    def consume_response(self, request_id: str) -> dict[str, Any] | None:
        with self._RAM_LOCK:
            return self._RAM_RESPONSES.pop(self._response_key(request_id), None)

    def cancel(self, request_id: str) -> bool:
        with self._lock:
            item = self._latest().get(request_id)
            if item is None or item.status not in {"PENDING", "RESPONDED"}:
                return False
            item.status = "CANCELLED"
            item.updated_at = time.time()
            self._append(item)
            with self._RAM_LOCK:
                self._RAM_RESPONSES.pop(self._response_key(request_id), None)
                self._RAM_CLAIMS.pop(request_id, None)
            return True

    def snapshot(self) -> dict[str, Any]:
        self.expire_stale()
        latest = self._latest()
        return {
            "pending": sum(x.status == "PENDING" for x in latest.values()),
            "responded_waiting_pc": sum(x.status == "RESPONDED" for x in latest.values()),
            "applied": sum(x.status == "APPLIED" for x in latest.values()),
            "requests": [
                self.public_item(x) for x in latest.values()
                if x.status in {"PENDING", "RESPONDED", "APPLIED"}
            ],
        }

    @staticmethod
    def _is_expired(item: HumanInteractionRequest) -> bool:
        return bool(item.expires_at and time.time() >= item.expires_at)

    def _response_key(self, request_id: str) -> str:
        return f"{self.root.resolve()}:{request_id}"

    def _append(self, item: HumanInteractionRequest) -> None:
        with self.requests_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(item), ensure_ascii=False) + "\n")

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
