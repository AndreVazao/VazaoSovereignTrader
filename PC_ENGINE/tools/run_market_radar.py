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
    try:
        while args.cycles == 0 or cycles < args.cycles:
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
            print(json.dumps(summary, ensure_ascii=False))
            cycles += 1
            if args.cycles == 0 or cycles < args.cycles:
                time.sleep(max(0.25, min(300.0, args.interval)))
    except KeyboardInterrupt:
        print("Radar stopped by user.")
    finally:
        radar.close()


if __name__ == "__main__":
    main()
