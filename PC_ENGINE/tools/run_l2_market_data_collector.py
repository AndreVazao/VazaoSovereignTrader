from __future__ import annotations

import argparse
import json
import signal
import threading
import time
from dataclasses import asdict
from pathlib import Path

from PC_ENGINE.market_events.l2_collectors import L2WebSocketConfig, PublicL2WebSocketCollector, default_l2_configs


SYNCHRONIZED_BOOK_FILENAMES = {
    "binance": "binance_synchronized_orderbook_views.jsonl",
    "coinbase": "coinbase_synchronized_orderbook_views.jsonl",
    "okx": "okx_synchronized_orderbook_views.jsonl",
}


def synchronized_book_path(data_dir: Path, venue: str) -> Path:
    """Return the dedicated output path for a supported synchronized venue."""
    try:
        filename = SYNCHRONIZED_BOOK_FILENAMES[venue]
    except KeyError as exc:
        raise ValueError("unsupported_synchronized_book_venue") from exc
    return data_dir / filename


def persist_synchronized_book(view, outputs: dict[str, Path], append_jsonl) -> None:
    """Persist a synchronized view to its venue-specific JSONL file.

    Unknown venues fail closed rather than being silently attributed to a
    different exchange's output file.
    """
    payload = asdict(view)
    status = getattr(view, "status", None)
    if hasattr(status, "value"):
        payload["status"] = status.value
    target = outputs.get(payload.get("venue"))
    if target is None:
        raise ValueError("unsupported_synchronized_book_venue")
    append_jsonl(target, payload)


def build_collector(config: L2WebSocketConfig, on_event, on_book) -> PublicL2WebSocketCollector:
    """Wire every supported venue to the synchronized-book callback."""
    callback = on_book if config.venue in SYNCHRONIZED_BOOK_FILENAMES else None
    return PublicL2WebSocketCollector(config, on_event, on_book=callback)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run public L2 order-book collection.")
    parser.add_argument("--symbols", nargs="+", default=["BTC/USDT", "ETH/USDT"])
    parser.add_argument("--venues", nargs="+", default=["binance", "okx", "coinbase"])
    parser.add_argument("--data-dir", default="PC_ENGINE/data/radar")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    output = data_dir / "websocket_orderbook_events.jsonl"
    synchronized_outputs = {venue: synchronized_book_path(data_dir, venue) for venue in SYNCHRONIZED_BOOK_FILENAMES}
    health_output = data_dir / "l2_collector_health.json"
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

    def persist_book(view) -> None:
        persist_synchronized_book(view, synchronized_outputs, append_jsonl)

    configs = []
    requested_venues = set(args.venues)
    for symbol in args.symbols:
        configs.extend(config for config in default_l2_configs(symbol) if config.venue in requested_venues)
    configured_pairs = {(config.symbol, config.venue) for config in configs}
    unconfigured_pairs = [
        {"symbol": symbol, "venue": venue, "reason": "no_safe_default_mapping"}
        for symbol in args.symbols for venue in args.venues
        if (symbol, venue) not in configured_pairs
    ]

    def write_health() -> None:
        while not stop.is_set():
            snapshot = {
                "service": "l2_market_data_collector",
                "updated_at_ms": time.time_ns() // 1_000_000,
                "paper_only": True,
                "orders_submitted": False,
                "unconfigured_pairs": unconfigured_pairs,
                "collectors": [collector.health_snapshot() for collector in collectors],
            }
            try:
                temporary = health_output.with_suffix(".json.tmp")
                temporary.write_text(json.dumps(snapshot, ensure_ascii=False, allow_nan=False), encoding="utf-8")
                temporary.replace(health_output)
            except OSError:
                # Health-file failure must not stop market-data collection.
                pass
            if stop.wait(5.0):
                break

    for config in configs:
        collector = build_collector(config, persist, persist_book)
        collectors.append(collector)
        thread = threading.Thread(
            target=collector.run_forever,
            name=f"l2-{config.venue}-{config.symbol.replace('/', '')}",
            daemon=True,
        )
        threads.append(thread)
        thread.start()

    health_thread = threading.Thread(target=write_health, name="l2-health-writer", daemon=True)
    health_thread.start()

    print(json.dumps({
        "service": "l2_market_data_collector",
        "status": "RUNNING",
        "symbols": args.symbols,
        "venues": args.venues,
        "configured_pairs": [{"symbol": symbol, "venue": venue} for symbol, venue in sorted(configured_pairs)],
        "unconfigured_pairs": unconfigured_pairs,
        "raw_output": str(output),
        "synchronized_book_outputs": {venue: str(path) for venue, path in synchronized_outputs.items()},
        "health_output": str(health_output),
        "paper_only": True,
        "orders_submitted": False,
    }, ensure_ascii=False))

    try:
        stop.wait()
    finally:
        stop.set()
        for collector in collectors:
            collector.stop()
        for thread in threads:
            thread.join(timeout=3)
        health_thread.join(timeout=2)
        print("L2 market-data collector stopped cleanly.")


if __name__ == "__main__":
    main()
