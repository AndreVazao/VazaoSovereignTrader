from __future__ import annotations

import threading
import time
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional

from PC_ENGINE.core.allocator import CapitalAllocator
from PC_ENGINE.core.risk import RiskEngine
from PC_ENGINE.core.strategy import TrendEmaAtrStrategy
from PC_ENGINE.exchanges.ccxt_client import CcxtExchangeClient
from PC_ENGINE.storage.ledger import Ledger


@dataclass
class Position:
    exchange: str
    symbol: str
    entry: float
    qty: float
    stop: float
    take_profit: float
    opened_ts: float


@dataclass
class RuntimeState:
    status: str = "OFF"
    mode: str = "PAPER"
    balance: float = 0.0
    equity: float = 0.0
    drawdown_pct: float = 0.0
    pnl_today_pct: float = 0.0
    pnl_week_pct: float = 0.0
    open_positions: Dict[str, Position] = field(default_factory=dict)
    asset_scores: Dict[str, float] = field(default_factory=dict)
    regimes: Dict[str, str] = field(default_factory=dict)
    logs: List[str] = field(default_factory=list)


class SovereignEngine:
    def __init__(self, config: dict):
        self.config = config
        self.mode = str(config.get("mode", "PAPER")).upper()
        self.paper = self.mode != "REAL"
        self.state = RuntimeState(mode=self.mode)
        self.ledger = Ledger()
        self.risk = RiskEngine(config["risk"])
        self.strategy = TrendEmaAtrStrategy(config["strategy"])
        self.allocator = CapitalAllocator(config["engine"], config.get("symbol_limits", {}))
        self.exchanges = self._build_exchanges()
        self.thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.lock = threading.RLock()

    def _build_exchanges(self) -> dict[str, CcxtExchangeClient]:
        out: dict[str, CcxtExchangeClient] = {}
        for name, cfg in self.config.get("exchanges", {}).items():
            if not cfg.get("enabled", False):
                continue
            out[name] = CcxtExchangeClient(
                name=name,
                key_env=cfg.get("key_env", ""),
                private_env=cfg.get("private_env", ""),
                paper=self.paper,
            )
        return out

    def log(self, message: str, data: dict | None = None) -> None:
        row = message if data is None else f"{message}: {data}"
        with self.lock:
            self.state.logs.append(row)
            self.state.logs = self.state.logs[-100:]
        self.ledger.event(message, data or {})

    def start(self) -> None:
        if self.thread and self.thread.is_alive():
            self.pause(False)
            return
        self.stop_event.clear()
        self.state.status = "RUNNING"
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()
        self.log("ENGINE_STARTED", {"mode": self.mode})

    def pause(self, paused: bool = True) -> None:
        with self.lock:
            self.state.status = "PAUSED" if paused else "RUNNING"
        self.log("ENGINE_PAUSED" if paused else "ENGINE_RESUMED")

    def stop(self) -> None:
        self.stop_event.set()
        with self.lock:
            self.state.status = "OFF"
        self.log("ENGINE_STOPPED")

    def set_mode(self, mode: str) -> None:
        mode = mode.upper()
        if mode not in {"PAPER", "REAL"}:
            raise ValueError("mode must be PAPER or REAL")
        if mode == "REAL" and self.state.status == "RUNNING":
            raise RuntimeError("Stop the engine before switching to REAL")
        self.mode = mode
        self.paper = mode != "REAL"
        self.state.mode = mode
        self.log("MODE_CHANGED", {"mode": mode})

    def snapshot(self) -> dict:
        with self.lock:
            data = asdict(self.state)
            data["open_positions"] = {k: asdict(v) for k, v in self.state.open_positions.items()}
            return data

    def _main_exchange(self) -> CcxtExchangeClient | None:
        return next(iter(self.exchanges.values()), None)

    def _loop(self) -> None:
        while not self.stop_event.is_set():
            if self.state.status == "PAUSED":
                time.sleep(1)
                continue
            try:
                self.cycle()
            except Exception as exc:
                self.state.status = "SAFE_MODE"
                self.log("ENGINE_ERROR_SAFE_MODE", {"error": str(exc)})
                time.sleep(15)
                self.state.status = "RUNNING"
            time.sleep(float(self.config["engine"].get("cycle_seconds", 20)))

    def cycle(self) -> None:
        exchange = self._main_exchange()
        if exchange is None:
            self.log("NO_EXCHANGE_ENABLED")
            return
        balance = exchange.free_quote_balance(self.config["engine"].get("quote_currency", "USDT"))
        if self.paper:
            balance = float(self.config["engine"].get("paper_starting_balance", 1000.0))
        equity = balance
        with self.lock:
            self.state.balance = balance
            self.state.equity = equity
        self.risk.update_equity(equity, float(self.config["engine"].get("paper_starting_balance", equity)))
        global_ok, global_reason = self.risk.can_trade_global()
        if not global_ok:
            self.state.status = "KILL_SWITCH"
            self.log("GLOBAL_RISK_BLOCK", {"reason": global_reason})
            return

        scores: dict[str, float] = {}
        signals = {}
        for symbol in self.config["symbols"]:
            try:
                ohlcv = exchange.fetch_ohlcv(symbol, self.config["strategy"]["timeframe"], int(self.config["strategy"]["candles_limit"]))
                spread_pct = exchange.fetch_spread_pct(symbol)
                signal = self.strategy.analyse(symbol, ohlcv, spread_pct)
                signals[symbol] = signal
                score = signal.strength * 100 if signal.action == "BUY" else 0.0
                scores[symbol] = score
                self.state.regimes[symbol] = signal.regime
            except Exception as exc:
                scores[symbol] = 0.0
                self.log("SYMBOL_ANALYSIS_ERROR", {"symbol": symbol, "error": str(exc)})

        allocations = self.allocator.allocate(equity, scores)
        with self.lock:
            self.state.asset_scores = scores
            self.state.drawdown_pct = self.risk.state.drawdown_pct
            self.state.pnl_today_pct = self.risk.state.pnl_today_pct
            self.state.pnl_week_pct = self.risk.state.pnl_week_pct

        # manage exits first
        for symbol, position in list(self.state.open_positions.items()):
            ticker = exchange.fetch_ticker(symbol)
            price = float(ticker.get("last") or 0.0)
            signal = signals.get(symbol)
            if price <= position.stop or price >= position.take_profit or (signal and signal.action == "SELL"):
                self._close_position(exchange, position, price, signal.reason if signal else "stop/take-profit")

        # open only best candidates if slots available
        for decision in allocations:
            symbol = decision.symbol
            if symbol in self.state.open_positions:
                continue
            if len(self.state.open_positions) >= int(self.config["engine"]["max_open_positions"]):
                break
            symbol_ok, reason = self.risk.can_trade_symbol(symbol)
            if not symbol_ok:
                self.log("SYMBOL_RISK_BLOCK", {"symbol": symbol, "reason": reason})
                continue
            signal = signals.get(symbol)
            if not signal or signal.action != "BUY":
                continue
            ticker = exchange.fetch_ticker(symbol)
            price = float(ticker.get("last") or 0.0)
            if price <= 0:
                continue
            notional = min(decision.max_notional, self.risk.position_notional(equity, signal.stop_pct))
            if notional <= 0:
                continue
            qty = notional / price
            self._open_position(exchange, symbol, price, qty, signal.stop_pct, signal.take_profit_pct, signal.reason)

    def _open_position(self, exchange: CcxtExchangeClient, symbol: str, price: float, qty: float, stop_pct: float, tp_pct: float, reason: str) -> None:
        exchange.market_buy(symbol, qty)
        position = Position(
            exchange=exchange.name,
            symbol=symbol,
            entry=price,
            qty=qty,
            stop=price * (1 - stop_pct),
            take_profit=price * (1 + tp_pct),
            opened_ts=time.time(),
        )
        with self.lock:
            self.state.open_positions[symbol] = position
        self.log("POSITION_OPENED", {"symbol": symbol, "price": price, "qty": qty, "reason": reason})

    def _close_position(self, exchange: CcxtExchangeClient, position: Position, price: float, reason: str) -> None:
        exchange.market_sell(position.symbol, position.qty)
        pnl_pct = (price - position.entry) / position.entry if position.entry else 0.0
        self.risk.record_trade_result(position.symbol, pnl_pct)
        with self.lock:
            self.state.open_positions.pop(position.symbol, None)
        self.ledger.trade({
            "exchange": position.exchange,
            "symbol": position.symbol,
            "side": "close",
            "qty": position.qty,
            "entry": position.entry,
            "exit": price,
            "pnl_pct": pnl_pct,
            "reason": reason,
        })
        self.log("POSITION_CLOSED", {"symbol": position.symbol, "pnl_pct": pnl_pct, "reason": reason})
