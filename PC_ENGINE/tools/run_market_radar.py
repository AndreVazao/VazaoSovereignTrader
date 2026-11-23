from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path

from PC_ENGINE.radar.market_radar import MarketRadar
from PC_ENGINE.radar.venue_discovery import VenueDiscoveryRegistry


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the observational Sovereign Market Radar")
    parser.add_argument(
        "--exchanges",
        default="",
        help="Optional comma-separated CCXT exchange IDs. By default use the reviewed public catalogue.",
    )
    parser.add_argument("--candidates", default="PC_ENGINE/config/exchange_candidates.json")
    parser.add_argument("--symbols", default="BTC/USDT,ETH/USDT", help="comma-separated symbols")
    parser.add_argument("--interval", type=float, default=5.0, help="seconds between snapshots")
    parser.add_argument("--cycles", type=int, default=0, help="0 means run continuously")
    parser.add_argument("--data-dir", default="PC_ENGINE/data/radar")
    parser.add_argument("--max-file-mb", type=float, default=64.0)
    parser.add_argument("--stop-file", default=None)
    args = parser.parse_args()

    registry = VenueDiscoveryRegistry(args.candidates)
    reviewed = {
        venue.venue_id: venue
        for venue in registry.list_venues()
        if venue.public_rest and venue.lifecycle == "public_research_only" and venue.ccxt_id
    }
    if args.exchanges.strip():
        requested = [x.strip().lower() for x in args.exchanges.split(",") if x.strip()]
        unknown = sorted(set(requested) - set(reviewed))
        if unknown:
            parser.error(
                "Exchange IDs are not reviewed public-data venues: " + ", ".join(unknown)
            )
        exchanges = list(dict.fromkeys(reviewed[name].ccxt_id for name in requested))
    else:
        exchanges = [reviewed[name].ccxt_id for name in sorted(reviewed)]

    if not exchanges:
        parser.error("No reviewed public REST venues are configured.")
    symbols = [x.strip() for x in args.symbols.split(",") if x.strip()]
    if not symbols:
        parser.error("At least one symbol is required.")
    if args.cycles < 0:
        parser.error("--cycles cannot be negative.")
    if not math.isfinite(args.max_file_mb) or args.max_file_mb <= 0:
        parser.error("--max-file-mb must be a finite positive number.")
    max_persist_bytes = min(512 * 1024 * 1024, max(1024, int(args.max_file_mb * 1024 * 1024)))

    radar = MarketRadar(
        exchanges, symbols, Path(args.data_dir), max_persist_bytes=max_persist_bytes
    )
    cycles = 0
    health_path = Path(args.data_dir) / "market_radar_health.json"

    def write_health(status: str, summary: dict | None = None) -> None:
        payload = {
            "schema_version": 1, "service": "market_radar_rest", "status": status,
            "timestamp_ms": time.time_ns() // 1_000_000,
            "configured_venues": exchanges, "symbols": symbols,
            "collection_metrics": radar.collection_metrics(), "summary": summary or {},
            "public_data_only": True, "private_account_access": False, "order_authority": False,
        }
        health_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = health_path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        temporary.replace(health_path)

    try:
        while (args.cycles == 0 or cycles < args.cycles) and not (args.stop_file and Path(args.stop_file).is_file()):
            snapshots, leads = radar.snapshot()
            summary = {
                "snapshots": len(snapshots),
                "pressure": radar.pressure(),
                "lead_lag_events": len(leads),
                "leaders": sorted({f"{x.leader}->{x.follower}" for x in leads}),
                "configured_venues": exchanges,
                "mode": "public_research_only",
                "max_persist_bytes": max_persist_bytes,
                "collection_metrics": radar.collection_metrics(),
            }
            write_health("RUNNING", summary)
            print(json.dumps(summary, ensure_ascii=False), flush=True)
            cycles += 1
            if args.cycles == 0 or cycles < args.cycles:
                wait_until = time.monotonic() + max(0.25, min(300.0, args.interval))
                while time.monotonic() < wait_until and not (args.stop_file and Path(args.stop_file).is_file()):
                    time.sleep(min(0.5, max(0.0, wait_until - time.monotonic())))
    except KeyboardInterrupt:
        print("Radar stopped by user.")
    finally:
        try:
            write_health("STOPPED")
        finally:
            radar.close()


if __name__ == "__main__":
    main()
