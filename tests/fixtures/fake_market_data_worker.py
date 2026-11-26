from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import time


HEALTH_FILES = {
    "VazaoSovereignTrader-Radar": "market_radar_health.json",
    "VazaoSovereignTrader-TopOfBook": "top_of_book_health.json",
    "VazaoSovereignTrader-L2": "l2_collector_health.json",
    "VazaoSovereignTrader-MarketData": "market_data_health.json",
}


def argument_after(name: str) -> str:
    try:
        index = sys.argv.index(name)
        return sys.argv[index + 1]
    except (ValueError, IndexError):
        raise SystemExit(f"missing_argument:{name}") from None


def main() -> int:
    executable_name = Path(sys.executable).stem
    health_name = HEALTH_FILES.get(executable_name)
    if health_name is None:
        raise SystemExit("unknown_fake_worker_executable")

    data_dir = Path(argument_after("--data-dir"))
    stop_file = Path(argument_after("--stop-file"))
    health_dir = data_dir / "radar"
    health_dir.mkdir(parents=True, exist_ok=True)
    health_path = health_dir / health_name
    temporary_path = health_path.with_suffix(health_path.suffix + ".tmp")

    try:
        ignore_seconds = max(0.0, min(30.0, float(os.environ.get(
            "VST_FAKE_WORKER_IGNORE_STOP_SECONDS", "0"
        ))))
    except ValueError:
        raise SystemExit("invalid_fake_worker_stop_delay") from None

    started = time.monotonic()
    while True:
        payload = {
            "status": "RUNNING",
            "timestamp_ms": time.time_ns() // 1_000_000,
            "fake_worker": True,
        }
        temporary_path.write_text(
            json.dumps(payload, sort_keys=True),
            encoding="utf-8",
        )
        temporary_path.replace(health_path)

        if stop_file.exists() and time.monotonic() - started >= ignore_seconds:
            return 0
        time.sleep(0.2)


if __name__ == "__main__":
    raise SystemExit(main())
