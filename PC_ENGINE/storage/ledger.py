from __future__ import annotations

import json
import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, List

from PC_ENGINE.core.config import LOG_DIR


class LedgerLockError(RuntimeError):
    """Ledger lock could not be acquired or released safely."""


@contextmanager
def _ledger_lock(path: Path) -> Iterator[None]:
    """Serialize idempotent ledger mutations across processes.

    The lock is an OS-level advisory/mandatory file lock on a persistent
    sibling file. No third-party dependency is required, and the lock is
    released automatically when the file descriptor closes.
    """
    lock_path = path.with_name(f"{path.name}.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = None
    try:
        handle = lock_path.open("a+b")
        handle.seek(0)
        if handle.read(1) == b"":
            handle.seek(0)
            handle.write(b"0")
            handle.flush()
        handle.seek(0)

        if os.name == "nt":
            import msvcrt

            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)

        yield
    except (OSError, ValueError) as exc:
        raise LedgerLockError("ledger lock unavailable") from exc
    finally:
        if handle is not None:
            try:
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except (OSError, ValueError):
                # The original operation is already fail-closed. Do not
                # replace it with a best-effort unlock failure.
                pass
            finally:
                handle.close()


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

    def trade_idempotent(self, record: Dict[str, Any], idempotency_key: str) -> bool:
        """Append a trade once for a durable reconciliation key."""
        key = str(idempotency_key or "").strip()
        if not key:
            raise ValueError("idempotency_key is required")

        with _ledger_lock(self.path):
            if self.path.exists():
                for line in self.path.read_text(encoding="utf-8").splitlines():
                    try:
                        row = json.loads(line)
                    except Exception:
                        continue
                    if str(row.get("reconciliation_key") or "").strip() == key:
                        return False
            row = {"ts": int(time.time()), "reconciliation_key": key, **record}
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
                f.flush()
                os.fsync(f.fileno())
            return True

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
