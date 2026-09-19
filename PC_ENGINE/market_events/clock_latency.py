"""Clock and latency calibration for normalized market events."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import median
from typing import Iterable, List, Optional


@dataclass(frozen=True)
class ClockLatencySample:
    venue: str
    venue_ts_ms: int
    local_receive_wall_ns: int
    local_receive_ns: int
    local_process_ns: Optional[int] = None

    @property
    def venue_wall_ns(self) -> int:
        return self.venue_ts_ms * 1_000_000

    @property
    def wall_offset_ns(self) -> int:
        return self.local_receive_wall_ns - self.venue_wall_ns

    @property
    def processing_delay_ns(self) -> Optional[int]:
        if self.local_process_ns is None:
            return None
        return self.local_process_ns - self.local_receive_ns


@dataclass(frozen=True)
class CalibrationStats:
    venue: str
    samples: int
    median_offset_ms: float
    p95_offset_ms: float
    p99_offset_ms: float
    jitter_ms: float
    median_processing_ms: Optional[float]


class ClockLatencyCalibrator:
    """Maintain rolling calibration statistics per venue."""

    def __init__(self, max_samples: int = 2000) -> None:
        if max_samples < 2:
            raise ValueError("max_samples must be >= 2")
        self.max_samples = max_samples
        self._samples: dict[str, List[ClockLatencySample]] = {}

    def add(self, sample: ClockLatencySample) -> None:
        if sample.venue_ts_ms <= 0:
            raise ValueError("venue_ts_ms must be positive")
        if sample.local_receive_wall_ns <= 0 or sample.local_receive_ns <= 0:
            raise ValueError("local timestamps must be positive")
        if sample.local_process_ns is not None and sample.local_process_ns < sample.local_receive_ns:
            raise ValueError("local_process_ns cannot precede local_receive_ns")
        bucket = self._samples.setdefault(sample.venue, [])
        bucket.append(sample)
        if len(bucket) > self.max_samples:
            del bucket[: len(bucket) - self.max_samples]

    def extend(self, samples: Iterable[ClockLatencySample]) -> None:
        for sample in samples:
            self.add(sample)

    @staticmethod
    def _percentile(values: List[float], percentile: float) -> float:
        ordered = sorted(values)
        if not ordered:
            raise ValueError("values must not be empty")
        if len(ordered) == 1:
            return ordered[0]
        rank = (len(ordered) - 1) * percentile
        lower = int(rank)
        upper = min(lower + 1, len(ordered) - 1)
        fraction = rank - lower
        return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction

    def stats(self, venue: str) -> Optional[CalibrationStats]:
        samples = self._samples.get(venue, [])
        if not samples:
            return None
        offsets = [s.wall_offset_ns / 1_000_000 for s in samples]
        processing = [
            s.processing_delay_ns / 1_000_000
            for s in samples
            if s.processing_delay_ns is not None
        ]
        med = median(offsets)
        jitter = median([abs(value - med) for value in offsets])
        return CalibrationStats(
            venue=venue,
            samples=len(samples),
            median_offset_ms=med,
            p95_offset_ms=self._percentile(offsets, 0.95),
            p99_offset_ms=self._percentile(offsets, 0.99),
            jitter_ms=jitter,
            median_processing_ms=median(processing) if processing else None,
        )

    def all_stats(self) -> dict[str, CalibrationStats]:
        return {
            venue: stats
            for venue in self._samples
            if (stats := self.stats(venue)) is not None
        }

    def venues(self) -> tuple[str, ...]:
        return tuple(sorted(self._samples))
