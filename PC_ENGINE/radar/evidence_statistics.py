from __future__ import annotations

import hashlib
import random
from typing import Sequence


def bootstrap_lower_ci(values: Sequence[float], *, seed_key: str, samples: int = 2000) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return float(values[0])
    samples = max(200, int(samples))
    seed = int.from_bytes(hashlib.sha256(seed_key.encode("utf-8")).digest()[:8], "big")
    rng = random.Random(seed)
    size = len(values)
    means = [sum(values[rng.randrange(size)] for _ in range(size)) / size for _ in range(samples)]
    means.sort()
    return means[max(0, int(0.025 * len(means)) - 1)]


def summary(values: Sequence[float]) -> tuple[int, int, float, float, float, float]:
    if not values:
        return 0, 0, 0.0, 0.0, 0.0, 0.0
    ordered = sorted(float(value) for value in values)
    samples = len(ordered)
    wins = sum(value > 0 for value in ordered)
    mean = sum(ordered) / samples
    mid = samples // 2
    median = ordered[mid] if samples % 2 else (ordered[mid - 1] + ordered[mid]) / 2.0
    variance = sum((value - mean) ** 2 for value in ordered) / samples
    se = variance ** 0.5 / samples ** 0.5 if samples > 1 else 0.0
    return samples, wins, wins / samples, mean, median, mean - 1.96 * se
