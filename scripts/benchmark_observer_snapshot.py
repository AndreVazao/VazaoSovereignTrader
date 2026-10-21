"""Microbenchmark the observer mailbox in isolation.

Run from the repository root:
    python scripts/benchmark_observer_snapshot.py --iterations 20000

This measures only the in-process latest-value mailbox. It does NOT measure
engine-cycle latency, engine-lock contention, HTTP serialization, CPU isolation,
or the impact of a saturated browser.
"""
from __future__ import annotations

import argparse
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PC_ENGINE.core.observer_snapshot import RuntimeObserverSnapshot  # noqa: E402


def percentile(sorted_values: list[int], fraction: float) -> int:
    index = min(len(sorted_values) - 1, int((len(sorted_values) - 1) * fraction))
    return sorted_values[index]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=20_000)
    args = parser.parse_args()
    if args.iterations < 100:
        parser.error("--iterations must be at least 100")

    mailbox = RuntimeObserverSnapshot()
    read_ns: list[int] = []
    write_ns: list[int] = []

    for index in range(args.iterations):
        started = time.perf_counter_ns()
        mailbox.publish(
            status="RUNNING",
            mode="PAPER",
            open_positions_count=index % 5,
            opportunities_count=index % 11,
            updated_at_ms=index + 1,
        )
        write_ns.append(time.perf_counter_ns() - started)

        started = time.perf_counter_ns()
        payload = mailbox.read()
        read_ns.append(time.perf_counter_ns() - started)
        if payload["updated_at_ms"] != index + 1:
            raise RuntimeError("latest-value contract violated")

    for label, samples in (("publish", write_ns), ("read", read_ns)):
        ordered = sorted(samples)
        print(
            f"{label}: n={len(ordered)} "
            f"p50={percentile(ordered, 0.50)}ns "
            f"p95={percentile(ordered, 0.95)}ns "
            f"p99={percentile(ordered, 0.99)}ns "
            f"max={max(ordered)}ns "
            f"mean={statistics.fmean(ordered):.1f}ns"
        )

    print(
        "LIMITATION: isolated mailbox microbenchmark only; "
        "do not interpret as Runtime cycle or end-to-end latency."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
