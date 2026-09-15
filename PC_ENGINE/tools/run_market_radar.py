from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from PC_ENGINE.radar.market_radar import MarketRadar


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the observational Sovereign Market Radar")
    parser.add_argument("--exchanges", default="binance,bingx,okx,bybit,coinbase", help="comma-separated CCXT exchange ids")
    parser.add_argument("--symbols", default="BTC/USDT,ETH/USDT", help="comma-separated symbols")
    parser.add_argument("--interval", type=float, default=5.0, help="seconds between snapshots")
    parser.add_argument("--cycles", type=int, default=0, help="0 means run continuously")
    parser.add_argument("--data-dir", default="PC_ENGINE/data/radar")
    args = parser.parse_args()

    radar = MarketRadar(
        [x.strip() for x in args.exchanges.split(",") if x.strip()],
        [x.strip() for x in args.symbols.split(",") if x.strip()],
        Path(args.data_dir),
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
            }
            print(json.dumps(summary, ensure_ascii=False))
            cycles += 1
            if args.cycles == 0 or cycles < args.cycles:
                time.sleep(max(0.25, args.interval))
    except KeyboardInterrupt:
        print("Radar stopped by user.")
    finally:
        radar.close()


if __name__ == "__main__":
    main()
