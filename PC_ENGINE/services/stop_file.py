from __future__ import annotations

from pathlib import Path
import threading
import time
from typing import Callable


def watch_stop_file(
    stop_event: threading.Event,
    path: str | Path,
    *,
    on_stop: Callable[[], None] | None = None,
    poll_seconds: float = 0.5,
) -> threading.Thread:
    """Watch a local control file and request cooperative worker shutdown."""
    target = Path(path)

    def watch() -> None:
        while not stop_event.wait(max(0.1, min(5.0, float(poll_seconds)))):
            if target.is_symlink() or not target.is_file():
                continue
            try:
                target.unlink()
            except OSError:
                # The request remains present and will be retried next poll.
                continue
            stop_event.set()
            if on_stop is not None:
                try:
                    on_stop()
                except Exception:
                    pass
            return

    thread = threading.Thread(target=watch, name="vst-stop-file-watch", daemon=True)
    thread.start()
    return thread
