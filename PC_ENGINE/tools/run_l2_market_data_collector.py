from __future__ import annotations

import argparse
import json
import signal
import threading
from dataclasses import asdict
from pathlib import Path

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
    stop = threading.Event()
    collectors: list[PublicL2WebSocketCollector] = []
    threads: list[threading.Thread] = []

    def shutdown(_signum, _frame) -> None:
        stop.set()
        for collector in collectors:
            collector.stop()

    signal.signal(signal.SIGINT, shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, shutdown)

    def persist(event) -> None:
        with output.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")

    configs = []
    for symbol in args.symbols:
        configs.extend(config for config in default_l2_configs(symbol) if config.venue in set(args.venues))

    for config in configs:
        collector = PublicL2WebSocketCollector(config, persist)
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
        "output": str(output),
        "paper_only": True,
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
