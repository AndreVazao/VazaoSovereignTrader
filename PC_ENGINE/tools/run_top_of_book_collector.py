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


def _write_health(
    path: Path,
    *,
    status: str,
    collectors: list[PublicWebSocketCollector],
    counters: dict[str, int],
    symbols: list[str],
    venues: list[str],
    output: Path,
    backup: Path,
    max_bytes: int,
) -> None:
    payload = {
        "schema_version": 1,
        "service": "top_of_book_collector",
        "status": status,
        "timestamp_ms": time.time_ns() // 1_000_000,
        "symbols": symbols,
        "venues": venues,
        "output": str(output),
        "backup": str(backup),
        "max_file_bytes": max_bytes,
        "collectors": [collector.snapshot() for collector in collectors],
        "counters": dict(counters),
        "paper_only": True,
        "orders_submitted": False,
        "execution_authorized": False,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def _is_valid_top_of_book(event) -> bool:
    """Reject malformed or economically invalid ticker values without raising."""
    try:
        bid = float(event.bid)
        ask = float(event.ask)
        receive_wall_ns = int(event.local_receive_wall_ns)
    except (AttributeError, TypeError, ValueError, OverflowError):
        return False
    return (
        math.isfinite(bid)
        and math.isfinite(ask)
        and bid > 0
        and ask > bid
        and receive_wall_ns > 0
    )


def _append_bounded_line(output: Path, backup: Path, encoded: str, max_bytes: int) -> bool:
    """Append one complete JSONL record without exceeding the configured file cap.

    Returns False when a single record is larger than the cap. In that case the
    current file is left untouched and the caller can count/drop the record.
    """
    encoded_size = len(encoded.encode("utf-8"))
    if encoded_size > max_bytes:
        return False
    if output.exists() and output.stat().st_size + encoded_size > max_bytes:
        if backup.exists():
            backup.unlink()
        output.replace(backup)
    with output.open("a", encoding="utf-8") as handle:
        handle.write(encoded)
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect public top-of-book ticker observations for PAPER research only."
    )
    parser.add_argument("--symbols", nargs="+", default=["BTC/USDT", "ETH/USDT"])
    parser.add_argument("--venues", nargs="+", default=["binance", "okx", "coinbase"])
    parser.add_argument("--data-dir", default="PC_ENGINE/data/radar")
    parser.add_argument("--max-file-mb", type=float, default=64.0)
    parser.add_argument("--health-interval-seconds", type=float, default=5.0)
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    output = data_dir / "websocket_ticker_events.jsonl"
    backup = output.with_suffix(output.suffix + ".1")
    health_path = data_dir / "top_of_book_health.json"
    max_bytes = max(1, int(args.max_file_mb * 1024 * 1024))
    health_interval = max(1.0, float(args.health_interval_seconds))
    stop = threading.Event()
    write_lock = threading.Lock()
    collectors: list[PublicWebSocketCollector] = []
    threads: list[threading.Thread] = []
    counters = {
        "events_written": 0,
        "invalid_tickers_ignored": 0,
        "oversized_tickers_ignored": 0,
        "write_errors": 0,
        "collector_errors": 0,
        "reconnects": 0,
    }
    counters_lock = threading.Lock()

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
        if not _is_valid_top_of_book(event):
            with counters_lock:
                counters["invalid_tickers_ignored"] += 1
            return
        row = event.as_dict()
        row.update({
            "paper_only": True,
            "orders_submitted": False,
            "execution_authorized": False,
            "observation_type": "PUBLIC_TOP_OF_BOOK",
        })
        encoded = json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
        with write_lock:
            try:
                if not _append_bounded_line(output, backup, encoded, max_bytes):
                    with counters_lock:
                        counters["oversized_tickers_ignored"] += 1
                    return
                with counters_lock:
                    counters["events_written"] += 1
            except OSError:
                with counters_lock:
                    counters["write_errors"] += 1

    def run_with_reconnect(collector: PublicWebSocketCollector) -> None:
        delay_seconds = 1.0
        while not stop.is_set():
            try:
                collector.run_forever()
            except Exception as exc:
                with counters_lock:
                    counters["collector_errors"] += 1
                print(json.dumps({
                    "service": "top_of_book_collector",
                    "venue": collector.config.venue,
                    "symbol": collector.config.symbol,
                    "collector_error": f"{type(exc).__name__}: {exc}",
                    "paper_only": True,
                }, ensure_ascii=False), flush=True)
            if stop.wait(delay_seconds):
                return
            with counters_lock:
                counters["reconnects"] += 1
            delay_seconds = min(15.0, delay_seconds * 2.0)

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
            target=run_with_reconnect,
            name=f"top-book-{cfg.venue}-{cfg.symbol.replace('/', '')}",
            args=(collector,),
            daemon=True,
        )
        threads.append(thread)
        thread.start()

    _write_health(
        health_path,
        status="RUNNING",
        collectors=collectors,
        counters=counters,
        symbols=args.symbols,
        venues=args.venues,
        output=output,
        backup=backup,
        max_bytes=max_bytes,
    )

    def health_loop() -> None:
        while not stop.wait(health_interval):
            try:
                _write_health(
                    health_path,
                    status="RUNNING",
                    collectors=collectors,
                    counters=counters,
                    symbols=args.symbols,
                    venues=args.venues,
                    output=output,
                    backup=backup,
                    max_bytes=max_bytes,
                )
            except OSError as exc:
                print(json.dumps({
                    "service": "top_of_book_collector",
                    "health_write_error": f"{type(exc).__name__}: {exc}",
                    "paper_only": True,
                }), flush=True)

    health_thread = threading.Thread(target=health_loop, name="top-book-health", daemon=True)
    health_thread.start()

    print(json.dumps({
        "service": "top_of_book_collector",
        "status": "RUNNING",
        "symbols": args.symbols,
        "venues": args.venues,
        "output": str(output),
        "backup": str(backup),
        "health": str(health_path),
        "health_interval_seconds": health_interval,
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
        health_thread.join(timeout=3)
        _write_health(
            health_path,
            status="STOPPED",
            collectors=collectors,
            counters=counters,
            symbols=args.symbols,
            venues=args.venues,
            output=output,
            backup=backup,
            max_bytes=max_bytes,
        )
        print(json.dumps({
            "service": "top_of_book_collector",
            "status": "STOPPED",
            **counters,
            "health": str(health_path),
            "paper_only": True,
            "orders_submitted": False,
            "execution_authorized": False,
        }, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
