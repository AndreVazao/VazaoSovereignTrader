from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from logging.handlers import RotatingFileHandler
import logging


@dataclass
class WorkerSpec:
    name: str
    command: tuple[str, ...]
    health_file: Path
    stale_after_seconds: float = 45.0
    process: subprocess.Popen | None = None
    last_start_ms: int = 0
    restarts: deque = field(default_factory=deque)
    last_exit_code: int | None = None
    last_error: str | None = None


class PublicMarketDataService:
    """Supervise only the fixed, public-data collector executables shipped with VST."""

    def __init__(
        self,
        app_dir: Path,
        data_dir: Path,
        *,
        symbols: list[str] | None = None,
        restart_limit: int = 8,
        restart_window_seconds: int = 900,
        health_interval_seconds: float = 5.0,
        popen=subprocess.Popen,
        clock=time.monotonic,
        sleep=time.sleep,
    ):
        self.app_dir = app_dir.resolve()
        self.data_dir = data_dir.resolve()
        self.symbols = list(dict.fromkeys(symbols or ["BTC/USDT", "ETH/USDT"]))
        self.restart_limit = max(1, int(restart_limit))
        self.restart_window_seconds = max(60, int(restart_window_seconds))
        self.health_interval_seconds = max(1.0, float(health_interval_seconds))
        self._popen = popen
        self._clock = clock
        self._sleep = sleep
        self._stop = threading.Event()
        self._lock = threading.RLock()
        self._logger = logging.getLogger("vst.market_data_service")
        self._logger.setLevel(logging.INFO)
        self._logger.propagate = False
        self.log_path = self.data_dir / "logs" / "market_data_service.log"
        self._logger.handlers.clear()
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(self.log_path, maxBytes=2 * 1024 * 1024, backupCount=2, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        self._logger.addHandler(handler)
        self.workers = self._build_workers()

    def _build_workers(self) -> list[WorkerSpec]:
        binaries = {
            "radar_rest": "VazaoSovereignTrader-Radar.exe",
            "top_of_book": "VazaoSovereignTrader-TopOfBook.exe",
            "order_book_l2": "VazaoSovereignTrader-L2.exe",
            "market_data_learning": "VazaoSovereignTrader-MarketData.exe",
        }
        commands = {
            "radar_rest": ("--symbols", ",".join(self.symbols), "--data-dir", str(self.data_dir / "radar")),
            "top_of_book": ("--symbols", *self.symbols, "--data-dir", str(self.data_dir / "radar")),
            "order_book_l2": ("--symbols", *self.symbols, "--data-dir", str(self.data_dir / "radar")),
            "market_data_learning": ("--data-dir", str(self.data_dir / "radar")),
        }
        health_names = {
            "radar_rest": "market_radar_health.json",
            "top_of_book": "top_of_book_health.json",
            "order_book_l2": "l2_collector_health.json",
            "market_data_learning": "market_data_health.json",
        }
        result = []
        for name, binary in binaries.items():
            executable = self.app_dir / binary
            if not executable.is_file():
                raise FileNotFoundError(f"required_worker_missing:{binary}")
            result.append(WorkerSpec(
                name=name,
                command=(str(executable), *commands[name]),
                health_file=self.data_dir / "radar" / health_names[name],
            ))
        return result

    def start(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "radar").mkdir(parents=True, exist_ok=True)
        self._logger.info("service starting; workers=%s", [w.name for w in self.workers])
        for worker in self.workers:
            self._start_worker(worker)
        self._write_health("RUNNING")

    def _start_worker(self, worker: WorkerSpec) -> bool:
        now = self._clock()
        while worker.restarts and now - worker.restarts[0] > self.restart_window_seconds:
            worker.restarts.popleft()
        if len(worker.restarts) >= self.restart_limit:
            worker.last_error = "restart_rate_limit_exceeded"
            self._logger.error("%s restart rate limit exceeded", worker.name)
            return False
        try:
            kwargs = {
                "cwd": str(self.app_dir),
                "stdin": subprocess.DEVNULL,
                "stdout": subprocess.DEVNULL,
                "stderr": subprocess.DEVNULL,
                "shell": False,
                "close_fds": True,
            }
            if os.name == "nt":
                kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            else:
                kwargs["start_new_session"] = True
            worker.process = self._popen(list(worker.command), **kwargs)
            worker.last_start_ms = time.time_ns() // 1_000_000
            worker.restarts.append(now)
            worker.last_error = None
            self._logger.info("worker started: %s pid=%s", worker.name, worker.process.pid)
            return True
        except Exception as exc:
            worker.process = None
            worker.last_error = type(exc).__name__
            self._logger.exception("worker start failed: %s", worker.name)
            return False

    def _health_age(self, worker: WorkerSpec) -> float | None:
        try:
            payload = json.loads(worker.health_file.read_text(encoding="utf-8"))
            stamp = int(payload.get("timestamp_ms") or payload.get("updated_at_ms") or 0)
            if not stamp:
                return None
            return max(0.0, (time.time_ns() // 1_000_000 - stamp) / 1000.0)
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return None

    def _worker_snapshot(self, worker: WorkerSpec) -> dict:
        process = worker.process
        running = process is not None and process.poll() is None
        age = self._health_age(worker)
        return {
            "running": running,
            "pid": getattr(process, "pid", None) if running else None,
            "health_file": str(worker.health_file),
            "health_age_seconds": age,
            "data_fresh": age is not None and age <= worker.stale_after_seconds,
            "restart_count_window": len(worker.restarts),
            "last_exit_code": worker.last_exit_code,
            "last_error": worker.last_error,
            "public_data_only": True,
            "order_authority": False,
        }

    def snapshot(self) -> dict:
        workers = {w.name: self._worker_snapshot(w) for w in self.workers}
        all_running = all(item["running"] for item in workers.values())
        all_fresh = all(item["data_fresh"] for item in workers.values())
        return {
            "schema_version": 1,
            "service": "vst_public_market_data",
            "status": "RUNNING" if all_running else "DEGRADED",
            "timestamp_ms": time.time_ns() // 1_000_000,
            "workers": workers,
            "all_workers_running": all_running,
            "all_data_fresh": all_fresh,
            "symbols": self.symbols,
            "data_dir": str(self.data_dir),
            "log_file": str(self.log_path),
            "paper_only": True,
            "private_account_access": False,
            "orders_submitted": False,
            "execution_authorized": False,
        }

    def _write_health(self, status: str) -> None:
        payload = self.snapshot()
        payload["status"] = status
        target = self.data_dir / "market_data_service_health.json"
        temporary = target.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        temporary.replace(target)

    def run(self) -> int:
        self.start()
        try:
            while not self._stop.wait(self.health_interval_seconds):
                changed = False
                for worker in self.workers:
                    process = worker.process
                    if process is not None and process.poll() is not None:
                        worker.last_exit_code = process.returncode
                        worker.process = None
                        worker.last_error = "worker_exited"
                        self._logger.warning("worker exited: %s code=%s", worker.name, worker.last_exit_code)
                        delay = min(60.0, 2.0 ** min(len(worker.restarts), 6))
                        if self._stop.wait(delay):
                            break
                        self._start_worker(worker)
                        changed = True
                try:
                    self._write_health("RUNNING" if all(w.process and w.process.poll() is None for w in self.workers) else "DEGRADED")
                except OSError:
                    self._logger.exception("health write failed")
            return 0
        finally:
            self.stop()

    def request_stop(self) -> None:
        self._stop.set()

    def stop(self) -> None:
        self._stop.set()
        for worker in reversed(self.workers):
            process = worker.process
            if process is None or process.poll() is not None:
                continue
            try:
                process.terminate()
                try:
                    process.wait(timeout=5.0)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=2.0)
            except Exception:
                self._logger.exception("worker shutdown failed: %s", worker.name)
            worker.process = None
        try:
            self._write_health("STOPPED")
        except OSError:
            self._logger.exception("final health write failed")
        self._logger.info("service stopped")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Supervise VST public market-data workers (PAPER only).")
    parser.add_argument("--app-dir", default=str(Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[2]))
    parser.add_argument("--data-dir", default=str(Path(os.environ.get("LOCALAPPDATA", Path.home())) / "VazaoSovereignTraderData" / "market-data"))
    parser.add_argument("--symbols", nargs="+", default=["BTC/USDT", "ETH/USDT"])
    parser.add_argument("--restart-limit", type=int, default=8)
    parser.add_argument("--restart-window-seconds", type=int, default=900)
    parser.add_argument("--health-interval-seconds", type=float, default=5.0)
    args = parser.parse_args(argv)
    if args.restart_limit < 1 or args.restart_window_seconds < 60 or not math_is_positive(args.health_interval_seconds):
        parser.error("restart limits and health interval must be positive and bounded")
    service = PublicMarketDataService(
        Path(args.app_dir), Path(args.data_dir), symbols=args.symbols,
        restart_limit=args.restart_limit,
        restart_window_seconds=args.restart_window_seconds,
        health_interval_seconds=args.health_interval_seconds,
    )
    def stop(_signum, _frame):
        service.request_stop()
    signal.signal(signal.SIGINT, stop)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, stop)
    return service.run()


def math_is_positive(value: float) -> bool:
    try:
        return float(value) > 0 and float(value) < 3600
    except (TypeError, ValueError):
        return False


if __name__ == "__main__":
    raise SystemExit(main())
