#!/usr/bin/env python3
"""Benchmark observer polling against real SovereignEngine PAPER cycles.

Uses deterministic synthetic OHLCV/ticker data and the production strategy,
allocator, risk checks, PAPER engine cycle, observer snapshot and authenticated
HTTP endpoint. The exchange adapter is synthetic; REAL mode and order entry are
disabled. This is not a live-exchange or profitability benchmark.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import tempfile
import threading
import time
from collections import deque
from pathlib import Path
from typing import Iterable

import PC_ENGINE.api.server as server_module
import PC_ENGINE.core.engine as engine_module
from PC_ENGINE.api.server import create_app
from PC_ENGINE.core.engine import SovereignEngine


class SyntheticPaperExchange:
    """Deterministic read-only exchange surface; it cannot submit orders."""

    name = "synthetic-paper"

    def __init__(self) -> None:
        self.ohlcv_calls = 0
        self.ticker_calls = 0
        self.spread_calls = 0

    def free_quote_balance(self, _currency: str) -> float:
        return 1_000.0

    def fetch_ohlcv(self, _symbol: str, _timeframe: str, limit: int) -> list[list[float]]:
        self.ohlcv_calls += 1
        now_ms = int(time.time() * 1000)
        end_ms = now_ms - (now_ms % 60_000)
        start_ms = end_ms - (limit - 1) * 60_000
        # Flat but non-zero-range candles exercise validation and indicators
        # while producing HOLD signals; max_open_positions is also set to zero.
        return [
            [start_ms + index * 60_000, 100.0, 100.2, 99.8, 100.0, 250.0]
            for index in range(limit)
        ]

    def fetch_spread_pct(self, _symbol: str) -> float:
        self.spread_calls += 1
        return 0.0002

    def fetch_ticker(self, _symbol: str) -> dict:
        self.ticker_calls += 1
        return {"last": 100.0, "timestamp": int(time.time() * 1000)}


def percentile(values: Iterable[int], fraction: float) -> int:
    ordered = sorted(values)
    if not ordered:
        return 0
    index = min(len(ordered) - 1, max(0, math.ceil(len(ordered) * fraction) - 1))
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


def _benchmark_config(isolated_root: Path) -> dict:
    config_path = Path(__file__).resolve().parents[1] / "PC_ENGINE" / "config" / "config.example.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config.setdefault("owner", {})["id"] = "paper-observer-load-benchmark"
    config["mode"] = "PAPER"
    config["exchanges"] = {}
    config.setdefault("engine", {})["max_open_positions"] = 0
    config["engine"]["cycle_seconds"] = 3600
    config["engine"]["preflight_required"] = False
    config.setdefault("watchdog", {})["enabled"] = False
    config.setdefault("radar", {})["enabled"] = False
    config.setdefault("research", {})["enabled"] = False
    config.setdefault("shared_intelligence", {})["enabled"] = False
    config["shared_intelligence"]["sync_enabled"] = False
    config.setdefault("learning_memory", {})["enabled"] = False
    config.setdefault("autonomous_execution", {})["enabled"] = False
    config["autonomous_execution"]["allow_real"] = False
    config["autonomous_execution"]["auto_promote_real"] = False
    opportunity = config.setdefault("opportunity", {})
    opportunity["data_dir"] = str(isolated_root / "market-state")
    opportunity["learning_path"] = str(isolated_root / "learning.jsonl")
    opportunity["latency_path"] = str(isolated_root / "latency.jsonl")
    opportunity["external_latency_profile_path"] = str(isolated_root / "external-latency.jsonl")
    config.setdefault("market_data_quality", {})["max_age_seconds"] = 120
    config["market_data_quality"]["max_gap_seconds"] = 180
    return config


def run_scenario(name: str, *, duration_seconds: float, readers: int, token: str) -> dict:
    previous_engine_data_dir = engine_module.DATA_DIR
    previous_server_data_dir = server_module.DATA_DIR
    previous_token = os.environ.get("VST_LOCAL_TOKEN")
    previous_vault_path = os.environ.get("VST_VAULT_PATH")
    engine = None
    with tempfile.TemporaryDirectory(prefix="vst-paper-observer-benchmark-") as temporary_dir:
        isolated_root = Path(temporary_dir)
        isolated_data_dir = isolated_root / "data"
        engine_module.DATA_DIR = isolated_data_dir
        server_module.DATA_DIR = isolated_data_dir
        os.environ["VST_LOCAL_TOKEN"] = token
        os.environ["VST_VAULT_PATH"] = str(isolated_root / "vault")
        try:
            engine = SovereignEngine(_benchmark_config(isolated_root))
            # Constructor starts its normal supervisor. Stop it before attaching
            # the synthetic adapter, then run cycles synchronously in this harness.
            engine.stop()
            engine.stop_event.clear()
            exchange = SyntheticPaperExchange()
            engine.exchanges = {exchange.name: exchange}
            app = create_app(engine)
            stop_readers = threading.Event()
            barrier = threading.Barrier(readers + 1)
            cycle_samples: deque[int] = deque(maxlen=100_000)
            request_samples: list[deque[int]] = [deque(maxlen=10_000) for _ in range(readers)]
            request_counts = [0 for _ in range(readers)]
            request_errors = [0 for _ in range(readers)]

            def poll(index: int) -> None:
                client = app.test_client()
                barrier.wait()
                while not stop_readers.is_set():
                    started = time.perf_counter_ns()
                    try:
                        response = client.get("/observer/summary", headers={"X-Token": token})
                        request_samples[index].append(time.perf_counter_ns() - started)
                        request_counts[index] += 1
                        if response.status_code != 200:
                            request_errors[index] += 1
                    except Exception:
                        request_samples[index].append(time.perf_counter_ns() - started)
                        request_errors[index] += 1

            threads = [
                threading.Thread(target=poll, args=(index,), name=f"paper-observer-reader-{index}", daemon=True)
                for index in range(readers)
            ]
            for thread in threads:
                thread.start()
            barrier.wait()
            started_at = time.perf_counter()
            deadline = started_at + duration_seconds
            engine_cycles = 0
            while time.perf_counter() < deadline:
                cycle_started = time.perf_counter_ns()
                engine.cycle()
                cycle_samples.append(time.perf_counter_ns() - cycle_started)
                engine_cycles += 1
            stop_readers.set()
            for thread in threads:
                thread.join(timeout=5)
            stuck = sum(thread.is_alive() for thread in threads)
            timing = engine.runtime_timing_metrics.snapshot()
            return {
                "scenario": name,
                "mode": engine.mode,
                "reader_threads": readers,
                "duration_seconds": round(time.perf_counter() - started_at, 3),
                "engine_cycles": engine_cycles,
                "runtime_cycle_latency": summarize(cycle_samples),
                "http_observer_summary_latency": summarize(
                    sample for samples in request_samples for sample in samples
                ),
                "http_requests": sum(request_counts),
                "http_errors": sum(request_errors),
                "reader_threads_still_running": stuck,
                "synthetic_market_data_calls": {
                    "ohlcv": exchange.ohlcv_calls,
                    "spread": exchange.spread_calls,
                    "ticker": exchange.ticker_calls,
                },
                "strategy_symbols_evaluated_last_cycle": len(engine.state.asset_scores),
                "open_positions": len(engine.state.open_positions),
                "pending_orders": len(engine.state.pending_orders),
                "execution_intents": len(engine.state.execution_intents),
                "runtime_timing_metrics": timing,
                "scope_note": (
                    "Full SovereignEngine PAPER cycle with production strategy, risk and allocator; "
                    "synthetic read-only market data; max_open_positions=0; no order entry or REAL access."
                ),
            }
        finally:
            try:
                if engine is not None:
                    engine.close()
            finally:
                engine_module.DATA_DIR = previous_engine_data_dir
                server_module.DATA_DIR = previous_server_data_dir
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

    token = f"paper-observer-benchmark-{os.urandom(16).hex()}"
    report = {
        "benchmark": "paper-engine-observer-load",
        "duration_seconds_per_scenario": args.duration_seconds,
        "scenarios": [
            run_scenario("office_absent", duration_seconds=args.duration_seconds, readers=0, token=token),
            run_scenario("normal_polling", duration_seconds=args.duration_seconds, readers=args.normal_readers, token=token),
            run_scenario("saturated_polling", duration_seconds=args.duration_seconds, readers=args.saturated_readers, token=token),
        ],
        "interpretation": (
            "Compare cycle and observer endpoint latency on the same host. This validates the "
            "synthetic PAPER cycle path only; it is not a live exchange, REAL execution, or profitability test."
        ),
    }
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
