from __future__ import annotations

import argparse
import json
import signal
import threading
from dataclasses import asdict
from pathlib import Path

from PC_ENGINE.market_events.binance_book_state import BookSnapshot
from PC_ENGINE.market_events.l2_collectors import PublicL2WebSocketCollector, default_l2_configs


def main() -> None:
    parser = argparse.ArgumentParser(description="Run public L2 order-book collection.")
    parser.add_argument("--symbols", nargs="+", default=["BTC/USDT", "ETH/USDT"])
    parser.add_argument("--venues", nargs="+", default=["binance", "okx", "coinbase"])
    parser.add_argument("--data-dir", default="PC_ENGINE/data/radar")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    output = data_dir / "websocket_orderbook_events.jsonl"
    synchronized_output = data_dir / "binance_synchronized_orderbook_views.jsonl"
    stop = threading.Event()
    write_lock = threading.Lock()
    collectors: list[PublicL2WebSocketCollector] = []
    threads: list[threading.Thread] = []

    def shutdown(_signum, _frame) -> None:
        stop.set()
        for collector in collectors:
            collector.stop()

    signal.signal(signal.SIGINT, shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, shutdown)

    def append_jsonl(path: Path, payload: dict) -> None:
        line = json.dumps(payload, ensure_ascii=False, allow_nan=False)
        with write_lock:
            with path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")

    def persist(event) -> None:
        append_jsonl(output, asdict(event))

    def persist_book(view: BookSnapshot) -> None:
        payload = asdict(view)
        payload["status"] = view.status.value
        append_jsonl(synchronized_output, payload)

    configs = []
    for symbol in args.symbols:
        configs.extend(config for config in default_l2_configs(symbol) if config.venue in set(args.venues))

    for config in configs:
        collector = PublicL2WebSocketCollector(
            config, persist,
            on_book=persist_book if config.venue == "binance" else None,
        )
        collectors.append(collector)
        thread = threading.Thread(
            target=collector.run_forever,
            name=f"l2-{config.venue}-{config.symbol.replace('/', '')}",
            daemon=True,
        )
        threads.append(thread)
        thread.start()

    print(json.dumps({
        "service": "l2_market_data_collector",
        "status": "RUNNING",
        "symbols": args.symbols,
        "venues": args.venues,
        "raw_output": str(output),
        "binance_synchronized_output": str(synchronized_output),
        "paper_only": True,
        "orders_submitted": False,
    }, ensure_ascii=False))

    try:
        stop.wait()
    finally:
        for collector in collectors:
            collector.stop()
        for thread in threads:
            thread.join(timeout=3)
        print("L2 market-data collector stopped cleanly.")


if __name__ == "__main__":
    main()
