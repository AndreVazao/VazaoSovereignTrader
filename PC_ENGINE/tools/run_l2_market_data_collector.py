from __future__ import annotations

import argparse
import json
import math
import signal
import threading
import time
from dataclasses import asdict
from pathlib import Path

from PC_ENGINE.market_events.binance_book_state import BookSnapshot
from PC_ENGINE.market_events.jsonl_store import append_bounded_jsonl
from PC_ENGINE.radar.collection_routing import reviewed_stream_venues
from PC_ENGINE.radar.venue_discovery import VenueDiscoveryRegistry
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


def build_collector(config: L2WebSocketConfig, on_event, on_book) -> PublicL2WebSocketCollector:
    """Wire each supported venue and preserve identity in synchronized callbacks."""
    callback = (
        (lambda view: on_book(config.venue, config.symbol, view))
        if config.venue in SYNCHRONIZED_BOOK_FILENAMES else None
    )
    return PublicL2WebSocketCollector(config, on_event, on_book=callback)


def synchronized_book_payload(venue: str, symbol: str, view) -> dict:
    """Serialize a synchronized view with explicit venue/instrument identity."""
    payload = asdict(view)
    if hasattr(view.status, "value"):
        payload["status"] = view.status.value
    payload["venue"] = venue
    payload["symbol"] = symbol
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Run public L2 order-book collection.")
    parser.add_argument("--symbols", nargs="+", default=["BTC/USDT", "ETH/USDT"])
    parser.add_argument("--venues", nargs="+", default=None)
    parser.add_argument("--candidates", default="PC_ENGINE/config/exchange_candidates.json")
    parser.add_argument("--data-dir", default="PC_ENGINE/data/radar")
    parser.add_argument("--max-file-mb", type=float, default=64.0)
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    output = data_dir / "websocket_orderbook_events.jsonl"
    synchronized_outputs = {venue: synchronized_book_path(data_dir, venue) for venue in SYNCHRONIZED_BOOK_FILENAMES}
    health_output = data_dir / "l2_collector_health.json"
    if not math.isfinite(args.max_file_mb) or args.max_file_mb <= 0:
        parser.error("--max-file-mb must be a finite positive number.")
    max_bytes = min(512 * 1024 * 1024, max(1024, int(args.max_file_mb * 1024 * 1024)))
    backups = {path: path.with_suffix(path.suffix + ".1") for path in [output, *synchronized_outputs.values()]}
    counters = {"events_written": 0, "books_written": 0, "oversized_records_ignored": 0, "write_errors": 0}
    counters_lock = threading.Lock()
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

    def append_jsonl(path: Path, payload: dict, counter: str) -> None:
        line = json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n"
        with write_lock:
            try:
                if not append_bounded_jsonl(path, backups[path], line, max_bytes):
                    with counters_lock:
                        counters["oversized_records_ignored"] += 1
                    return
                with counters_lock:
                    counters[counter] += 1
            except OSError:
                with counters_lock:
                    counters["write_errors"] += 1

    def persist(event) -> None:
        append_jsonl(output, asdict(event), "events_written")

    def persist_book(venue: str, symbol: str, view) -> None:
        payload = synchronized_book_payload(venue, symbol, view)
        target = synchronized_outputs.get(venue)
        if target is None:
            raise ValueError("unsupported_synchronized_book_venue")
        append_jsonl(target, payload, "books_written")

    registry = VenueDiscoveryRegistry(args.candidates)
    available = {
        config.venue
        for symbol in args.symbols
        for config in default_l2_configs(symbol)
    }
    try:
        selected_venues = reviewed_stream_venues(registry, available, args.venues)
    except ValueError as exc:
        parser.error(str(exc))
    if not selected_venues:
        parser.error("No reviewed native public L2 venues are available.")
    configs = []
    requested_venues = set(selected_venues)
    for symbol in args.symbols:
        configs.extend(config for config in default_l2_configs(symbol) if config.venue in requested_venues)
    configured_pairs = {(config.symbol, config.venue) for config in configs}
    unconfigured_pairs = [
        {"symbol": symbol, "venue": venue, "reason": "no_safe_default_mapping"}
        for symbol in args.symbols for venue in selected_venues
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
                "max_file_bytes": max_bytes,
                "backups": {"raw": str(backups[output]), **{venue: str(backups[path]) for venue, path in synchronized_outputs.items()}},
                "counters": dict(counters),
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
        "venues": selected_venues,
        "configured_pairs": [{"symbol": symbol, "venue": venue} for symbol, venue in sorted(configured_pairs)],
        "unconfigured_pairs": unconfigured_pairs,
        "raw_output": str(output),
        "synchronized_book_outputs": {venue: str(path) for venue, path in synchronized_outputs.items()},
        "health_output": str(health_output),
        "max_file_bytes": max_bytes,
        "counters": dict(counters),
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
