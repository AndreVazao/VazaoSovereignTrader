from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


class OperatorExchange:
    """Small authenticated file bridge for the mobile cockpit.

    Only two directories are exposed:
    INBOX  = operator -> PC
    OUTBOX = PC -> operator

    No arbitrary filesystem paths are accepted.
    """

    FOLDERS = {"INBOX", "OUTBOX"}

    def __init__(self, root: str | Path, max_upload_mb: int = 25) -> None:
        self.root = Path(root)
        self.max_upload_bytes = max(1, int(max_upload_mb)) * 1024 * 1024
        for folder in self.FOLDERS:
            (self.root / folder).mkdir(parents=True, exist_ok=True)

    def _folder(self, folder: str) -> Path:
        normalized = str(folder).strip().upper()
        if normalized not in self.FOLDERS:
            raise ValueError("invalid_operator_exchange_folder")
        return self.root / normalized

    @staticmethod
    def _safe_name(name: str) -> str:
        candidate = Path(str(name)).name
        candidate = _SAFE_NAME.sub("_", candidate).strip(" .")
        if not candidate or candidate in {".", ".."}:
            raise ValueError("invalid_operator_exchange_filename")
        return candidate[:180]

    def list_files(self, folder: str) -> list[dict[str, Any]]:
        path = self._folder(folder)
        rows = []
        for item in sorted(path.iterdir(), key=lambda p: p.name.lower()):
            if not item.is_file():
                continue
            stat = item.stat()
            rows.append({
                "name": item.name,
                "size": stat.st_size,
                "modified_ms": int(stat.st_mtime_ns // 1_000_000),
                "sha256": self._sha256(item),
            })
        return rows

    def save_upload(self, folder: str, filename: str, stream) -> dict[str, Any]:
        if str(folder).upper() != "INBOX":
            raise PermissionError("mobile_uploads_are_inbox_only")
        path = self._folder("INBOX") / self._safe_name(filename)
        total = 0
        tmp = path.with_suffix(path.suffix + ".uploading")
        try:
            with tmp.open("wb") as handle:
                while True:
                    chunk = stream.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > self.max_upload_bytes:
                        raise ValueError("operator_exchange_upload_too_large")
                    handle.write(chunk)
                handle.flush()
            tmp.replace(path)
        finally:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
        return self.describe("INBOX", path.name)

    def resolve_download(self, folder: str, filename: str) -> Path:
        path = self._folder(folder) / self._safe_name(filename)
        if not path.exists() or not path.is_file():
            raise FileNotFoundError("operator_exchange_file_not_found")
        return path

    def describe(self, folder: str, filename: str) -> dict[str, Any]:
        path = self.resolve_download(folder, filename)
        stat = path.stat()
        return {
            "folder": str(folder).upper(),
            "name": path.name,
            "size": stat.st_size,
            "modified_ms": int(stat.st_mtime_ns // 1_000_000),
            "sha256": self._sha256(path),
        }

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
