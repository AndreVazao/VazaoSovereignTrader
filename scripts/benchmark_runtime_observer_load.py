#!/usr/bin/env python3
"""Measure observer/API load against the Runtime cycle wrapper without trading.

This is a controlled observer-path benchmark, NOT a full strategy/exchange
benchmark: _cycle_once is replaced with a no-op so no market data or orders are
requested. It measures cycle-wrapper + observer publication overhead while the
authenticated /observer/summary endpoint is idle, polled normally, or saturated.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import tempfile
import threading
import time
from collections import deque
from pathlib import Path
from typing import Iterable

import PC_ENGINE.core.engine as engine_module
from PC_ENGINE.api.server import create_app
from PC_ENGINE.core.engine import SovereignEngine


def percentile(values: Iterable[int], fraction: float) -> int:
    ordered = sorted(values)
    if not ordered:
        return 0
    index = min(len(ordered) - 1, max(0, int(__import__("math").ceil(len(ordered) * fraction)) - 1))
    return int(ordered[index])


def summarize(values: Iterable[int]) -> dict[str, int]:
    captured = list(values)
    if not captured:
        return {"count": 0, "p50_ns": 0, "p95_ns": 0, "p99_ns": 0, "max_ns": 0, "mean_ns": 0}
    return {
        "count": len(captured),
        "p50_ns": percentile(captured, 0.50),
        "p95_ns": percentile(captured, 0.95),
        "p99_ns": percentile(captured, 0.99),
        "max_ns": max(captured),
        "mean_ns": int(statistics.fmean(captured)),
    }


def run_scenario(name: str, *, duration_seconds: float, readers: int, token: str) -> dict:
    config_path = Path(__file__).resolve().parents[1] / "PC_ENGINE" / "config" / "config.example.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config.setdefault("owner", {})["id"] = f"observer-load-benchmark-{name}"
    config.setdefault("radar", {})["enabled"] = False
    config.setdefault("shared_intelligence", {})["sync_enabled"] = False
    config["exchanges"] = {}

    previous_data_dir = engine_module.DATA_DIR
    previous_token = os.environ.get("VST_LOCAL_TOKEN")
    with tempfile.TemporaryDirectory(prefix="vst-observer-benchmark-") as temporary_dir:
        engine_module.DATA_DIR = Path(temporary_dir) / "data"
        os.environ["VST_LOCAL_TOKEN"] = token
        try:
            engine = SovereignEngine(config)
            # Isolate the observer path. Never call exchange adapters or strategy.
            engine._cycle_once = lambda: None
            app = create_app(engine)
            stop = threading.Event()
            barrier = threading.Barrier(readers + 1)
            cycle_samples: deque[int] = deque(maxlen=100_000)
            request_samples: list[deque[int]] = [deque(maxlen=5_000) for _ in range(readers)]
            request_counts = [0 for _ in range(readers)]
            request_errors = [0 for _ in range(readers)]

            def poll(index: int) -> None:
                client = app.test_client()
                barrier.wait()
                while not stop.is_set():
                    started = time.perf_counter_ns()
                    try:
                        response = client.get("/observer/summary", headers={"X-Token": token})
                        elapsed = time.perf_counter_ns() - started
                        request_samples[index].append(elapsed)
                        request_counts[index] += 1
                        if response.status_code != 200:
                            request_errors[index] += 1
                    except Exception:
                        request_errors[index] += 1
                        request_samples[index].append(time.perf_counter_ns() - started)

            threads = [
                threading.Thread(target=poll, args=(index,), name=f"observer-reader-{index}", daemon=True)
                for index in range(readers)
            ]
            for thread in threads:
                thread.start()
            barrier.wait()
            started_at = time.perf_counter()
            deadline = started_at + duration_seconds
            while time.perf_counter() < deadline:
                cycle_started = time.perf_counter_ns()
                engine.cycle()
                cycle_samples.append(time.perf_counter_ns() - cycle_started)
            stop.set()
            for thread in threads:
                thread.join(timeout=5)
            stuck = sum(thread.is_alive() for thread in threads)
            all_request_samples = [sample for samples in request_samples for sample in samples]
            timing = engine.runtime_timing_metrics.snapshot()
            return {
                "scenario": name,
                "reader_threads": readers,
                "duration_seconds": round(time.perf_counter() - started_at, 3),
                "runtime_cycle_wrapper_latency": summarize(cycle_samples),
                "http_observer_summary_latency": summarize(all_request_samples),
                "http_requests": sum(request_counts),
                "http_errors": sum(request_errors),
                "reader_threads_still_running": stuck,
                "runtime_timing_metrics": timing,
                "scope_note": "No-op _cycle_once; no strategy, market-data fetch, or order execution. This isolates observer-path contention only.",
            }
        finally:
            engine_module.DATA_DIR = previous_data_dir
            if previous_token is None:
                os.environ.pop("VST_LOCAL_TOKEN", None)
            else:
                os.environ["VST_LOCAL_TOKEN"] = previous_token


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duration-seconds", type=float, default=3.0)
    parser.add_argument("--normal-readers", type=int, default=1)
    parser.add_argument("--saturated-readers", type=int, default=16)
    args = parser.parse_args()
    if not 0.2 <= args.duration_seconds <= 30:
        parser.error("--duration-seconds must be between 0.2 and 30")
    if not 0 <= args.normal_readers <= 8:
        parser.error("--normal-readers must be between 0 and 8")
    if not 1 <= args.saturated_readers <= 64:
        parser.error("--saturated-readers must be between 1 and 64")

    token = f"benchmark-{os.urandom(16).hex()}"
    report = {
        "benchmark": "runtime-observer-load",
        "duration_seconds_per_scenario": args.duration_seconds,
        "scenarios": [
            run_scenario("office_absent", duration_seconds=args.duration_seconds, readers=0, token=token),
            run_scenario("normal_polling", duration_seconds=args.duration_seconds, readers=args.normal_readers, token=token),
            run_scenario("saturated_polling", duration_seconds=args.duration_seconds, readers=args.saturated_readers, token=token),
        ],
        "interpretation": "Compare p50/p95/p99/max across scenarios on the same host. Do not infer production trading-cycle latency or CPU/process isolation from this no-op benchmark.",
    }
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
