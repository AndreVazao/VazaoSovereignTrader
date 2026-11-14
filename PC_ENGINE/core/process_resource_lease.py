from __future__ import annotations

import errno
import os
import threading
import time
from pathlib import Path
from typing import BinaryIO


_ALLOWED_KINDS = frozenset({"backtest", "simulation", "analysis"})
_MAX_SLOTS = 32
_ADMISSION_TIMEOUT_SECONDS = 2.0

_PROCESS_STATE_LOCK = threading.Lock()
_PROCESS_ACTIVE: dict[tuple[str, str], int] = {}
_PROCESS_ADMISSION_LOCKS: dict[tuple[str, str], threading.Lock] = {}


def _ensure_lock_byte(handle: BinaryIO) -> None:
    handle.seek(0, os.SEEK_END)
    if handle.tell() == 0:
        handle.write(b"\0")
        handle.flush()
    handle.seek(0)


def _try_lock(handle: BinaryIO) -> bool:
    handle.seek(0)
    if os.name == "nt":
        import msvcrt

        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            return True
        except OSError:
            return False

    import fcntl

    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError as exc:
        if exc.errno in (errno.EACCES, errno.EAGAIN):
            return False
        raise


def _lock_with_timeout(handle: BinaryIO, timeout_seconds: float) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while True:
        if _try_lock(handle):
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.01)


def _unlock(handle: BinaryIO) -> None:
    try:
        handle.seek(0)
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    except OSError:
        # Closing the handle still releases the operating-system lock.
        pass


def _unlock_and_close(handle: BinaryIO) -> None:
    try:
        _unlock(handle)
    finally:
        handle.close()


class ProcessResourceLease:
    """Crash-released, cross-process admission slot for optional heavy work.

    A short-lived admission lock serializes slot selection. The selected slot
    stays OS-locked for the job lifetime, so another process cannot exceed the
    current per-kind budget. The OS releases the slot if its process exits.
    """

    def __init__(
        self,
        root: str | Path,
        kind: str,
        limit: int,
        *,
        max_slots: int = _MAX_SLOTS,
        admission_timeout_seconds: float = _ADMISSION_TIMEOUT_SECONDS,
    ) -> None:
        if kind not in _ALLOWED_KINDS:
            raise ValueError("unsupported_resource_lease_kind")
        if isinstance(limit, bool) or not isinstance(limit, int):
            raise ValueError("invalid_resource_lease_limit")
        if not 1 <= limit <= max_slots <= _MAX_SLOTS:
            raise ValueError("invalid_resource_lease_limit")
        if not 0.1 <= float(admission_timeout_seconds) <= 10.0:
            raise ValueError("invalid_resource_lease_timeout")

        self.root = Path(root)
        self.kind = kind
        self.limit = limit
        self.max_slots = max_slots
        self.admission_timeout_seconds = float(admission_timeout_seconds)
        self._key = (str(self.root.resolve()), self.kind)
        self._lease_handle: BinaryIO | None = None
        self._reserved = False

    def acquire(self) -> bool:
        if self._lease_handle is not None:
            return True

        try:
            self.root.mkdir(parents=True, exist_ok=True)
        except OSError:
            return False

        with _PROCESS_STATE_LOCK:
            active = _PROCESS_ACTIVE.get(self._key, 0)
            if active >= self.limit:
                return False
            _PROCESS_ACTIVE[self._key] = active + 1
            process_admission = _PROCESS_ADMISSION_LOCKS.setdefault(
                self._key, threading.Lock()
            )
            self._reserved = True

        if not process_admission.acquire(timeout=self.admission_timeout_seconds):
            self._release_process_reservation()
            return False

        try:
            admission_path = self.root / f"{self.kind}.admission.lock"
            with admission_path.open("a+b") as admission:
                _ensure_lock_byte(admission)
                if not _lock_with_timeout(
                    admission, self.admission_timeout_seconds
                ):
                    return False

                free_handles: list[BinaryIO] = []
                busy_slots = 0
                try:
                    for slot in range(self.max_slots):
                        slot_path = self.root / f"{self.kind}-{slot:02d}.lock"
                        handle = slot_path.open("a+b")
                        _ensure_lock_byte(handle)
                        if _try_lock(handle):
                            free_handles.append(handle)
                        else:
                            busy_slots += 1
                            handle.close()

                    if busy_slots >= self.limit or not free_handles:
                        return False

                    self._lease_handle = free_handles.pop(0)
                    return True
                finally:
                    for handle in free_handles:
                        _unlock_and_close(handle)
                    _unlock(admission)
        except OSError:
            return False
        finally:
            process_admission.release()
            if self._lease_handle is None:
                self._release_process_reservation()

    def release(self) -> None:
        handle = self._lease_handle
        self._lease_handle = None
        if handle is not None:
            _unlock_and_close(handle)
        self._release_process_reservation()

    def _release_process_reservation(self) -> None:
        if not self._reserved:
            return
        with _PROCESS_STATE_LOCK:
            active = _PROCESS_ACTIVE.get(self._key, 0)
            if active <= 1:
                _PROCESS_ACTIVE.pop(self._key, None)
            else:
                _PROCESS_ACTIVE[self._key] = active - 1
            self._reserved = False
