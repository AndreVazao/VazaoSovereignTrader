from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PC_ENGINE.backtest.replay import ReplayBacktester
from PC_ENGINE.core.config import DATA_DIR, load_config
from PC_ENGINE.core.adaptive_resource_manager import AdaptiveResourceManager
from PC_ENGINE.core.adaptive_job_gate import AdaptiveJobGate, AdaptiveJobDeferred
from PC_ENGINE.core.strategy import TrendEmaAtrStrategy
from PC_ENGINE.exchanges.ccxt_client import CcxtExchangeClient


def main() -> None:
    parser = argparse.ArgumentParser(description="Run PAPER backtest/replay using live historical candles.")
    parser.add_argument("--exchange", default="binance")
    parser.add_argument("--symbol", default="BTC/USDT")
    parser.add_argument("--limit", type=int, default=500)
    args = parser.parse_args()

    config = load_config()
    ex_cfg = config["exchanges"].get(args.exchange)
    if not ex_cfg:
        raise SystemExit(f"Exchange not found in config: {args.exchange}")

    exchange = CcxtExchangeClient(
        name=args.exchange,
        key_env=ex_cfg.get("key_env", ""),
        private_env=ex_cfg.get("private_env", ""),
        paper=True,
    )
    candles = exchange.fetch_ohlcv(args.symbol, config["strategy"]["timeframe"], args.limit)
    strategy = TrendEmaAtrStrategy(config["strategy"])
    paper = config.get("paper", {})
    adaptive_cfg = dict(config.get("adaptive_resources", {}))
    resource_manager = None
    if bool(adaptive_cfg.get("enabled", True)):
        resource_manager = AdaptiveResourceManager(root=DATA_DIR, reserve_memory_mb=int(adaptive_cfg.get("reserve_memory_mb", 512)), max_workers_cap=adaptive_cfg.get("max_workers_cap"))
    backtester = ReplayBacktester(
        strategy,
        fee_pct=float(paper.get("fee_pct", 0.001)),
        slippage_pct=float(paper.get("slippage_pct", 0.0005)),
        job_gate=AdaptiveJobGate(resource_manager) if resource_manager is not None else None,
    )
    try:
        result = backtester.run(args.symbol, candles)
    except AdaptiveJobDeferred as exc:
        raise SystemExit(f"Backtest deferred safely: {exc}") from exc
    print(json.dumps(result.__dict__, indent=2))


if __name__ == "__main__":
    main()
