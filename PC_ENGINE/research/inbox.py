from __future__ import annotations

import json
import os
import re
import time
import uuid
from contextlib import contextmanager
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
    lease_owner: str = ""
    lease_expires_at: float = 0.0
    attempt_count: int = 0


class TraderResearchInbox:
    """Append-only research queue with cross-process claims and expiring leases.

    Claims are advisory research work only. A lease never conveys trading authority.
    """

    def __init__(self, data_dir: str = "PC_ENGINE/data/research"):
        self.root = Path(data_dir)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "requests.jsonl"
        self.lock_path = self.root / "requests.lock"

    @contextmanager
    def _file_lock(self):
        """Serialize read/append/claim across threads and processes on Windows and POSIX."""
        with self.lock_path.open("a+b") as handle:
            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(b"0")
                handle.flush()
            handle.seek(0)
            if os.name == "nt":
                import msvcrt
                while True:
                    try:
                        msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
                        break
                    except OSError:
                        time.sleep(0.05)
                try:
                    yield
                finally:
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def submit(self, message: str) -> ResearchRequest:
        message = str(message or "").strip()
        if not message:
            raise ValueError("research_message_required")
        now = time.time()
        item = ResearchRequest(
            request_id=uuid.uuid4().hex,
            message=message,
            urls=self._extract_urls(message),
            status="PENDING",
            created_at=now,
            updated_at=now,
        )
        self._append(item)
        return item

    def claim_next(
        self, owner: str, *, lease_seconds: float = 300.0, max_attempts: int = 3
    ) -> ResearchRequest | None:
        owner = str(owner or "").strip()
        if not owner:
            raise ValueError("research_lease_owner_required")
        lease_seconds = max(30.0, min(float(lease_seconds), 3600.0))
        max_attempts = max(1, min(int(max_attempts), 10))
        now = time.time()
        with self._file_lock():
            latest = self._latest_unlocked()
            candidates = sorted(latest.values(), key=lambda x: x.created_at)
            for item in candidates:
                eligible = item.status == "PENDING" or (
                    item.status == "IN_PROGRESS" and item.lease_expires_at <= now
                )
                if not eligible:
                    continue
                if item.attempt_count >= max_attempts:
                    item.status = "FAILED"
                    item.result = "Pesquisa terminou sem conclusão após o limite de tentativas."
                    item.lease_owner = ""
                    item.lease_expires_at = 0.0
                    item.updated_at = now
                    self._append_unlocked(item)
                    continue
                item.status = "IN_PROGRESS"
                item.lease_owner = owner
                item.lease_expires_at = now + lease_seconds
                item.attempt_count += 1
                item.updated_at = now
                self._append_unlocked(item)
                return item
        return None

    def renew_lease(self, request_id: str, owner: str, *, lease_seconds: float = 300.0) -> bool:
        now = time.time()
        with self._file_lock():
            latest = self._latest_unlocked()
            item = latest.get(request_id)
            if item is None or item.status != "IN_PROGRESS" or item.lease_owner != owner:
                return False
            if item.lease_expires_at <= now:
                return False
            item.lease_expires_at = now + max(30.0, min(float(lease_seconds), 3600.0))
            item.updated_at = now
            self._append_unlocked(item)
            return True

    def complete(self, request_id: str, owner: str, *, status: str, result: str) -> bool:
        if status not in {"COMPLETED", "DISCARDED"}:
            raise ValueError("invalid_research_terminal_status")
        with self._file_lock():
            latest = self._latest_unlocked()
            item = latest.get(request_id)
            if item is None or item.status != "IN_PROGRESS" or item.lease_owner != owner:
                return False
            if item.lease_expires_at <= time.time():
                return False
            item.status = status
            item.result = str(result or "")[:20_000]
            item.lease_owner = ""
            item.lease_expires_at = 0.0
            item.updated_at = time.time()
            self._append_unlocked(item)
            return True

    def release(self, request_id: str, owner: str, *, error_type: str, max_attempts: int = 3) -> bool:
        with self._file_lock():
            latest = self._latest_unlocked()
            item = latest.get(request_id)
            if item is None or item.status != "IN_PROGRESS" or item.lease_owner != owner:
                return False
            item.status = "FAILED" if item.attempt_count >= max(1, int(max_attempts)) else "PENDING"
            item.result = f"Falha de processamento: {str(error_type or 'UnknownError')[:120]}"
            item.lease_owner = ""
            item.lease_expires_at = 0.0
            item.updated_at = time.time()
            self._append_unlocked(item)
            return True

    def snapshot(self) -> dict:
        latest = self._latest()
        items = [asdict(x) for x in latest.values()]
        items.sort(key=lambda x: x["created_at"], reverse=True)
        return {
            "pending": sum(x["status"] == "PENDING" for x in items),
            "active": sum(x["status"] == "IN_PROGRESS" for x in items),
            "completed": sum(x["status"] == "COMPLETED" for x in items),
            "discarded": sum(x["status"] == "DISCARDED" for x in items),
            "failed": sum(x["status"] == "FAILED" for x in items),
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
        with self._file_lock():
            self._append_unlocked(item)

    def _append_unlocked(self, item: ResearchRequest) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(item), ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    def _latest(self) -> dict[str, ResearchRequest]:
        with self._file_lock():
            return self._latest_unlocked()

    def _latest_unlocked(self) -> dict[str, ResearchRequest]:
        latest: dict[str, ResearchRequest] = {}
        if not self.path.exists():
            return latest
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    payload = json.loads(line)
                    # Older JSONL records predate lease fields; dataclass defaults preserve them.
                    item = ResearchRequest(**payload)
                    latest[item.request_id] = item
                except (TypeError, ValueError, json.JSONDecodeError):
                    continue
        return latest
