from __future__ import annotations

import argparse
import json
import math
import signal
import threading
import time
from pathlib import Path

from PC_ENGINE.market_events.websocket_collectors import (
    PublicWebSocketCollector,
    default_public_configs,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect public top-of-book ticker observations for PAPER research only."
    )
    parser.add_argument("--symbols", nargs="+", default=["BTC/USDT", "ETH/USDT"])
    parser.add_argument("--venues", nargs="+", default=["binance", "okx", "coinbase"])
    parser.add_argument("--data-dir", default="PC_ENGINE/data/radar")
    parser.add_argument("--max-file-mb", type=float, default=64.0)
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    output = data_dir / "websocket_ticker_events.jsonl"
    backup = output.with_suffix(output.suffix + ".1")
    max_bytes = max(1, int(args.max_file_mb * 1024 * 1024))
    stop = threading.Event()
    write_lock = threading.Lock()
    collectors: list[PublicWebSocketCollector] = []
    threads: list[threading.Thread] = []
    counters = {"events_written": 0, "invalid_tickers_ignored": 0}

    def shutdown(_signum, _frame) -> None:
        stop.set()
        for collector in collectors:
            collector.stop()

    signal.signal(signal.SIGINT, shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, shutdown)

    def persist(event) -> None:
        if event.event_type != "ticker":
            return
        bid, ask = event.bid, event.ask
        if (
            bid is None or ask is None
            or not math.isfinite(float(bid)) or not math.isfinite(float(ask))
            or float(bid) <= 0 or float(ask) <= float(bid)
            or int(event.local_receive_wall_ns) <= 0
        ):
            with write_lock:
                counters["invalid_tickers_ignored"] += 1
            return
        row = event.as_dict()
        row.update({
            "paper_only": True,
            "orders_submitted": False,
            "execution_authorized": False,
            "observation_type": "PUBLIC_TOP_OF_BOOK",
        })
        encoded = json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\\n"
        with write_lock:
            try:
                if output.exists() and output.stat().st_size + len(encoded.encode("utf-8")) > max_bytes:
                    if backup.exists():
                        backup.unlink()
                    output.replace(backup)
                with output.open("a", encoding="utf-8") as handle:
                    handle.write(encoded)
                counters["events_written"] += 1
            except OSError:
                counters["invalid_tickers_ignored"] += 1

    allowed = set(args.venues)
    configs = [
        cfg
        for symbol in args.symbols
        for cfg in default_public_configs(symbol)
        if cfg.venue in allowed
    ]
    for cfg in configs:
        collector = PublicWebSocketCollector(cfg, persist)
        collectors.append(collector)
        thread = threading.Thread(
            target=collector.run_forever,
            name=f"top-book-{cfg.venue}-{cfg.symbol.replace('/', '')}",
            daemon=True,
        )
        threads.append(thread)
        thread.start()

    print(json.dumps({
        "service": "top_of_book_collector",
        "status": "RUNNING",
        "symbols": args.symbols,
        "venues": args.venues,
        "output": str(output),
        "backup": str(backup),
        "max_file_bytes": max_bytes,
        "paper_only": True,
        "orders_submitted": False,
        "execution_authorized": False,
    }, ensure_ascii=False), flush=True)

    try:
        stop.wait()
    finally:
        for collector in collectors:
            collector.stop()
        for thread in threads:
            thread.join(timeout=3)
        print(json.dumps({
            "service": "top_of_book_collector",
            "status": "STOPPED",
            **counters,
            "paper_only": True,
            "orders_submitted": False,
            "execution_authorized": False,
        }, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
