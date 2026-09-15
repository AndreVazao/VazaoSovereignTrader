from __future__ import annotations

import json
import queue
import threading
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Callable, Mapping


@dataclass(frozen=True)
class LearningEvent:
    symbol: str
    action: str
    timestamp_ms: int
    payload: dict[str, Any]


class SlowLearningQueue:
    """Bounded background queue so learning never blocks market decisions."""

    def __init__(self, data_dir: str | Path = "PC_ENGINE/data/radar", maxsize: int = 5000,
                 processor: Callable[[LearningEvent], None] | None = None) -> None:
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.queue: queue.Queue[LearningEvent] = queue.Queue(maxsize=max(1, int(maxsize)))
        self.processor = processor
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.dropped = 0
        self.processed = 0

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="slow-learning", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 2.0) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=max(0.0, timeout))
        self._thread = None

    def submit(self, event: LearningEvent) -> bool:
        """Non-blocking submit. False means the bounded queue is full."""
        try:
            self.queue.put_nowait(event)
            return True
        except queue.Full:
            self.dropped += 1
            return False

    def submit_mapping(self, symbol: str, action: str, timestamp_ms: int,
                       payload: Mapping[str, Any]) -> bool:
        return self.submit(LearningEvent(symbol, action, int(timestamp_ms), dict(payload)))

    def snapshot(self) -> dict[str, int | bool]:
        return {
            "running": bool(self._thread and self._thread.is_alive()),
            "queued": self.queue.qsize(),
            "processed": self.processed,
            "dropped": self.dropped,
        }

    def _run(self) -> None:
        path = self.data_dir / "slow_learning_events.jsonl"
        while not self._stop.is_set() or not self.queue.empty():
            try:
                event = self.queue.get(timeout=0.1)
            except queue.Empty:
                continue
            try:
                if self.processor is not None:
                    self.processor(event)
                with path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")
                self.processed += 1
            finally:
                self.queue.task_done()
