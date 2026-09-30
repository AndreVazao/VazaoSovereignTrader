from __future__ import annotations

import argparse
import json
import signal
import threading
import time
from pathlib import Path

from PC_ENGINE.radar.lead_lag_learning import LeadLagLearningEngine
from PC_ENGINE.radar.websocket_radar import WebSocketMarketRadar


REPO_ROOT = Path(__file__).resolve().parents[2]


def _resolve_path(raw: str) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else REPO_ROOT / path


def _load_config(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run continuous public market-data collection and PAPER learning."
    )
    parser.add_argument(
        "--config",
        default=str(REPO_ROOT / "PC_ENGINE" / "config" / "config.local.json"),
    )
    parser.add_argument("--data-dir", default=None)
    parser.add_argument("--learn-minutes", type=float, default=5.0)
    args = parser.parse_args()

    config = _load_config(_resolve_path(args.config))
    radar_cfg = config.get("radar", {})
    symbols = list(radar_cfg.get("websocket_symbols") or config.get("symbols") or ["BTC/USDT", "ETH/USDT"])
    exchanges = list(radar_cfg.get("websocket_exchanges") or ["binance", "coinbase", "okx"])
    data_dir = _resolve_path(args.data_dir or radar_cfg.get("data_dir") or "PC_ENGINE/data/radar")
    data_dir.mkdir(parents=True, exist_ok=True)
    health_path = data_dir / "market_data_health.json"

    def write_health(status: str, **extra) -> None:
        payload = {
            "service": "market_data_collector",
            "status": status,
            "timestamp_ms": time.time_ns() // 1_000_000,
            "symbols": symbols,
            "exchanges": exchanges,
            "data_dir": str(data_dir),
            "paper_only": True,
            **extra,
        }
        tmp = health_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        tmp.replace(health_path)

    stop = threading.Event()

    def shutdown(_signum, _frame) -> None:
        stop.set()

    signal.signal(signal.SIGINT, shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, shutdown)

    radar = WebSocketMarketRadar(
        symbols=symbols,
        exchanges=exchanges,
        data_dir=data_dir,
        min_move_bps=float(radar_cfg.get("min_move_bps", 5)),
        lead_window_ms=int(radar_cfg.get("lead_window_ms", 750)),
    )
    learner = LeadLagLearningEngine(
        data_dir=data_dir,
        min_samples=int(radar_cfg.get("lead_lag_min_samples", 100)),
        fee_bps_per_side=float(radar_cfg.get("lead_lag_fee_bps_per_side", 10)),
        slippage_bps_per_side=float(radar_cfg.get("lead_lag_slippage_bps_per_side", 4)),
        response_threshold_bps=float(radar_cfg.get("lead_lag_response_threshold_bps", 2)),
    )

    radar.start()
    write_health("RUNNING", radar=radar.snapshot())
    print(json.dumps({
        "service": "market_data_collector",
        "status": "RUNNING",
        "symbols": symbols,
        "exchanges": exchanges,
        "data_dir": str(data_dir),
        "paper_only": True,
    }, ensure_ascii=False), flush=True)

    next_learning = 0.0
    try:
        while not stop.is_set():
            now = time.monotonic()
            if now >= next_learning:
                stats = learner.learn()
                radar_state = radar.snapshot()
                write_health(
                    "RUNNING",
                    radar=radar_state,
                    learning={
                        "stats": len(stats),
                        "eligible_paper_relationships": sum(1 for row in stats if row.eligible),
                    },
                )
                print(json.dumps({
                    "service": "market_data_collector",
                    "stats": len(stats),
                    "eligible_paper_relationships": sum(1 for row in stats if row.eligible),
                    "timestamp_ms": time.time_ns() // 1_000_000,
                }, ensure_ascii=False), flush=True)
                next_learning = now + max(30.0, args.learn_minutes * 60.0)
            stop.wait(1.0)
    finally:
        radar.stop()
        learner.learn()
        write_health("STOPPED", radar=radar.snapshot())
        print("Market-data collector stopped cleanly.", flush=True)


if __name__ == "__main__":
    main()
