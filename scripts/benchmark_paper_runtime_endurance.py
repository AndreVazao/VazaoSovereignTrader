#!/usr/bin/env python3
"""Measure bounded-duration PAPER runtime endurance and Python allocation growth.

The engine uses the production cycle/strategy/risk path with a deterministic,
read-only synthetic exchange. REAL authorization and order entry are disabled.
tracemalloc measures Python allocations, not total process RSS or GPU/native memory.
"""
from __future__ import annotations

import argparse
import json
import os
import tracemalloc

from scripts.benchmark_paper_engine_observer_load import run_scenario


def run_endurance(*, duration_seconds: float, readers: int, token: str) -> dict:
    tracemalloc.start()
    try:
        before_current, _ = tracemalloc.get_traced_memory()
        result = run_scenario(
            "paper_runtime_endurance",
            duration_seconds=duration_seconds,
            readers=readers,
            token=token,
        )
        after_current, peak = tracemalloc.get_traced_memory()
        result["python_memory"] = {
            "current_before_bytes": before_current,
            "current_after_bytes": after_current,
            "net_growth_bytes": after_current - before_current,
            "peak_traced_bytes": peak,
            "measurement": "tracemalloc Python allocations only; not process RSS or native allocations",
        }
        return result
    finally:
        tracemalloc.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duration-seconds", type=float, default=30.0)
    parser.add_argument("--readers", type=int, default=2)
    args = parser.parse_args()
    if not 0.2 <= args.duration_seconds <= 300:
        parser.error("--duration-seconds must be between 0.2 and 300")
    if not 0 <= args.readers <= 16:
        parser.error("--readers must be between 0 and 16")

    report = {
        "benchmark": "paper-runtime-endurance",
        "duration_seconds_requested": args.duration_seconds,
        "scenario": run_endurance(
            duration_seconds=args.duration_seconds,
            readers=args.readers,
            token=f"paper-endurance-{os.urandom(16).hex()}",
        ),
        "interpretation": (
            "Synthetic-exchange PAPER engine endurance only. Memory figures are Python "
            "tracemalloc allocations, not total process RSS. No REAL exchange or orders."
        ),
    }
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
