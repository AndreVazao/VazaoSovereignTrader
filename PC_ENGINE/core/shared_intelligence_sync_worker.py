from __future__ import annotations

import random
import threading
import time
from typing import Any

from .shared_intelligence import SharedIntelligenceStore
from .shared_intelligence_sync import SharedIntelligenceProvider, SharedIntelligenceSync


class SharedIntelligenceSyncWorker:
    """Best-effort maintenance worker; never controls execution or REAL authorization."""

    def __init__(
        self,
        store: SharedIntelligenceStore,
        sync: SharedIntelligenceSync,
        provider: SharedIntelligenceProvider,
        *,
        pull_interval_seconds: float = 86400.0,
        push_interval_seconds: float = 86400.0,
        initial_jitter_seconds: float = 30.0,
        jitter_fraction: float = 0.10,
        retry_base_seconds: float = 60.0,
        retry_max_seconds: float = 3600.0,
    ):
        self.store = store
        self.sync = sync
        self.provider = provider
        self.pull_interval = max(60.0, float(pull_interval_seconds))
        self.push_interval = max(60.0, float(push_interval_seconds))
        self.initial_jitter_seconds = max(0.0, min(float(initial_jitter_seconds), 900.0))
        self.jitter_fraction = max(0.0, min(float(jitter_fraction), 0.25))
        self.retry_base_seconds = max(1.0, float(retry_base_seconds))
        self.retry_max_seconds = max(self.retry_base_seconds, float(retry_max_seconds))
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None
        self.bootstrap_done = False
        self.last_result: dict[str, Any] = {}
        self._pull_failures = 0
        self._push_failures = 0

    def _jittered_interval(self, interval: float) -> float:
        spread = interval * self.jitter_fraction
        return max(1.0, interval + random.uniform(-spread, spread))

    def _retry_delay(self, failures: int) -> float:
        exponent = max(0, min(int(failures) - 1, 20))
        delay = min(self.retry_max_seconds, self.retry_base_seconds * (2 ** exponent))
        # Jitter avoids synchronized retries across many independent owner nodes.
        return max(1.0, random.uniform(delay * 0.75, delay))

    def start(self) -> None:
        if self.thread and self.thread.is_alive():
            return
        self.stop_event.clear()
        self.thread = threading.Thread(
            target=self._run,
            name="shared-intelligence-sync",
            daemon=True,
        )
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)

    def run_once(self, *, bootstrap: bool = False) -> dict[str, Any]:
        pull = (
            self.sync.bootstrap(self.provider)
            if bootstrap
            else self.sync.sync_once(self.provider)
        )
        push = self.sync.push_new(self.provider)
        if bootstrap:
            self.bootstrap_done = True
        self.last_result = {"pull": pull, "push": push}
        return self.last_result

    def _run(self) -> None:
        # Delay initial network work so engine startup and local operation stay responsive.
        initial_delay = random.uniform(0.0, self.initial_jitter_seconds)
        if self.stop_event.wait(initial_delay):
            return
        now = time.monotonic()
        next_pull = now
        next_push = now
        while not self.stop_event.is_set():
            now = time.monotonic()
            if now >= next_pull:
                try:
                    result = (
                        self.sync.bootstrap(self.provider)
                        if not self.bootstrap_done
                        else self.sync.sync_once(self.provider)
                    )
                    self.bootstrap_done = True
                    self._pull_failures = 0
                    self.last_result["pull"] = result
                    next_pull = time.monotonic() + self._jittered_interval(self.pull_interval)
                except Exception as exc:
                    self._pull_failures += 1
                    self.last_result["pull_error"] = type(exc).__name__
                    next_pull = time.monotonic() + self._retry_delay(self._pull_failures)

            if self.stop_event.is_set():
                break

            now = time.monotonic()
            if now >= next_push:
                try:
                    result = self.sync.push_new(self.provider)
                    self._push_failures = 0
                    self.last_result["push"] = result
                    next_push = time.monotonic() + self._jittered_interval(self.push_interval)
                except Exception as exc:
                    self._push_failures += 1
                    self.last_result["push_error"] = type(exc).__name__
                    next_push = time.monotonic() + self._retry_delay(self._push_failures)

            due_in = max(0.25, min(next_pull, next_push) - time.monotonic())
            self.stop_event.wait(min(due_in, 30.0))
