from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Iterable

from PC_ENGINE.radar.external_source_adapter import (
    ExternalSourceAdapter,
    observation_quality,
    validate_observation,
)


@dataclass
class ExternalSourceHealth:
    source_id: str
    polls: int = 0
    observations: int = 0
    accepted: int = 0
    rejected: int = 0
    errors: int = 0
    last_poll_ms: int = 0
    last_observation_ms: int = 0
    last_transport_latency_ms: float | None = None
    last_error: str | None = None
    sequence_gaps: int = 0
    last_sequence: int | None = None


class ExternalSourceSupervisor:
    """PAPER/research-only supervisor for compliant external market-data adapters.

    Adapters are pull-only and normalized before entering the radar. This component
    never submits orders, changes trading mode, or grants execution authority.
    """

    def __init__(
        self,
        radar,
        adapters: Iterable[ExternalSourceAdapter] = (),
        poll_interval_seconds: float = 1.0,
        max_observations_per_poll: int = 500,
        max_silence_seconds: float = 5.0,
        clock_ms=None,
    ) -> None:
        self.radar = radar
        self.adapters = list(adapters)
        self.poll_interval_seconds = max(0.05, float(poll_interval_seconds))
        self.max_observations_per_poll = max(1, int(max_observations_per_poll))
        self.max_silence_ms = max(250, int(float(max_silence_seconds) * 1000))
        self.clock_ms = clock_ms or (lambda: time.time_ns() // 1_000_000)
        self.health = {
            str(adapter.source_id): ExternalSourceHealth(str(adapter.source_id))
            for adapter in self.adapters
        }
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.RLock()
        self._last_sequence: dict[str, int] = {}

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._loop,
            name="external-source-supervisor",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=max(1.0, self.poll_interval_seconds + 1.0))
        self._thread = None

    def poll_once(self) -> int:
        accepted = 0
        for adapter in self.adapters:
            source_id = str(adapter.source_id).strip()
            health = self.health.setdefault(source_id, ExternalSourceHealth(source_id))
            now = int(self.clock_ms())
            health.polls += 1
            health.last_poll_ms = now
            try:
                observations = list(adapter.poll())
                for observation in observations[: self.max_observations_per_poll]:
                    health.observations += 1
                    try:
                        validate_observation(observation)
                        quality = observation_quality(observation)
                        if not quality["clock_order_valid"]:
                            raise ValueError("source_clock_order_invalid")
                        if observation.sequence is not None:
                            sequence = int(observation.sequence)
                            previous = self._last_sequence.get(source_id)
                            if previous is not None and sequence > previous + 1:
                                health.sequence_gaps += 1
                            if previous is None or sequence > previous:
                                self._last_sequence[source_id] = sequence
                            health.last_sequence = self._last_sequence[source_id]
                        self.radar.ingest_external_observation(observation)
                        health.accepted += 1
                        health.last_observation_ms = int(
                            observation.received_ts_ms or observation.source_ts_ms
                        )
                        health.last_transport_latency_ms = float(
                            quality["transport_latency_ms"]
                        )
                        accepted += 1
                    except Exception as exc:
                        health.rejected += 1
                        health.last_error = str(exc)
            except Exception as exc:
                health.errors += 1
                health.last_error = str(exc)
        return accepted

    def snapshot(self) -> dict:
        with self._lock:
            now = int(self.clock_ms())
            sources = {}
            for source_id, item in self.health.items():
                age_ms = (
                    max(0, now - item.last_observation_ms)
                    if item.last_observation_ms
                    else None
                )
                fresh = age_ms is not None and age_ms <= self.max_silence_ms
                sources[source_id] = {
                    "polls": item.polls,
                    "observations": item.observations,
                    "accepted": item.accepted,
                    "rejected": item.rejected,
                    "errors": item.errors,
                    "last_poll_ms": item.last_poll_ms,
                    "last_observation_ms": item.last_observation_ms,
                    "last_observation_age_ms": age_ms,
                    "last_transport_latency_ms": item.last_transport_latency_ms,
                    "last_error": item.last_error,
                    "sequence_gaps": item.sequence_gaps,
                    "last_sequence": item.last_sequence,
                    "fresh": fresh,
                    "healthy": (
                        item.errors == 0
                        and item.rejected == 0
                        and fresh
                    ),
                }
            return {
                "running": bool(self._thread and self._thread.is_alive()),
                "poll_interval_seconds": self.poll_interval_seconds,
                "max_silence_seconds": self.max_silence_ms / 1000,
                "adapter_count": len(self.adapters),
                "sources": sources,
            }

    def _loop(self) -> None:
        while not self._stop.is_set():
            started = time.monotonic()
            try:
                self.poll_once()
            except Exception:
                # The supervisor is non-critical research telemetry; never stop
                # the trading engine because an adapter supervisor failed.
                pass
            elapsed = time.monotonic() - started
            self._stop.wait(max(0.0, self.poll_interval_seconds - elapsed))
