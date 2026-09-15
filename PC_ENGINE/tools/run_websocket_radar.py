from __future__ import annotations

import argparse
import signal
import time

from PC_ENGINE.radar.websocket_radar import WebSocketMarketRadar


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the observation-only WebSocket Market Radar")
    parser.add_argument("--symbols", default="BTC/USDT,ETH/USDT", help="Comma-separated symbols")
    parser.add_argument("--exchanges", default="binance,coinbase,okx", help="Comma-separated native WebSocket adapters")
    parser.add_argument("--seconds", type=int, default=0, help="0 = run until Ctrl+C")
    parser.add_argument("--min-move-bps", type=float, default=5.0)
    parser.add_argument("--lead-window-ms", type=int, default=750)
    args = parser.parse_args()

    radar = WebSocketMarketRadar(
        symbols=[x.strip().upper() for x in args.symbols.split(",") if x.strip()],
        exchanges=[x.strip().lower() for x in args.exchanges.split(",") if x.strip()],
        min_move_bps=args.min_move_bps,
        lead_window_ms=args.lead_window_ms,
    )

    def shutdown(_signum: int, _frame: object) -> None:
        radar.stop()

    signal.signal(signal.SIGINT, shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, shutdown)

    radar.start()
    print(f"WebSocket Radar ativo: {radar.exchanges} | {radar.symbols}")
    print("Observação apenas — não existem ordens nem acesso a contas privadas.")
    started = time.monotonic()
    try:
        while not radar._stop.is_set():
            if args.seconds > 0 and time.monotonic() - started >= args.seconds:
                break
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        radar.stop()
        print("WebSocket Radar parado.")


if __name__ == "__main__":
    main()
