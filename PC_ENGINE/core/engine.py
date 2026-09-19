from __future__ import annotations

import threading
import time
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional

from PC_ENGINE.ai_council.stub import DisabledAICouncil
from PC_ENGINE.core.allocator import CapitalAllocator
from PC_ENGINE.core.opportunity import PaperOpportunityEngine
from PC_ENGINE.core.exchange_rules import ExchangeRulesEngine
from PC_ENGINE.core.order_manager import OrderManager
from PC_ENGINE.core.paper_broker import PaperBroker
from PC_ENGINE.core.preflight import PreflightChecker
from PC_ENGINE.core.recovery import RecoveryManager
from PC_ENGINE.core.risk import RiskEngine
from PC_ENGINE.core.strategy import TrendEmaAtrStrategy
from PC_ENGINE.exchanges.ccxt_client import CcxtExchangeClient
from PC_ENGINE.learning.champion_challenger import ChampionChallenger
from PC_ENGINE.services.paper_market_collector import PaperMarketCollector
from PC_ENGINE.services.watchdog import Watchdog
from PC_ENGINE.radar.market_state import MarketStateStore
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
    entry_fee: float = 0.0


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
    opportunities: Dict[str, dict] = field(default_factory=dict)
    regimes: Dict[str, str] = field(default_factory=dict)
    watchdog: Dict[str, str | bool | int] = field(default_factory=dict)
    preflight: Dict[str, object] = field(default_factory=dict)
    champion_challenger: Dict[str, object] = field(default_factory=dict)
    paper_collector: Dict[str, object] = field(default_factory=dict)
    logs: List[str] = field(default_factory=list)


class SovereignEngine:
    def __init__(self, config: dict):
        self.config = config
        self.mode = str(config.get("mode", "PAPER")).upper()
        self.paper = self.mode != "REAL"
        self.state = RuntimeState(mode=self.mode)
        self.ledger = Ledger()
        self.rules = ExchangeRulesEngine()
        paper_cfg = config.get("paper", {})
        self.paper_broker = PaperBroker(
            fee_pct=float(paper_cfg.get("fee_pct", 0.001)),
            slippage_pct=float(paper_cfg.get("slippage_pct", 0.0005)),
            reject_probability=float(paper_cfg.get("reject_probability", 0.0)),
        )
        self.order_manager = OrderManager(self.rules, self.paper_broker)
        self.recovery = RecoveryManager()
        self.watchdog = Watchdog()
        self.ai_council = DisabledAICouncil()
        self.champion = ChampionChallenger()
        self.risk = RiskEngine(config["risk"])
        self.strategy = TrendEmaAtrStrategy(config["strategy"])
        self.allocator = CapitalAllocator(config["engine"], config.get("symbol_limits", {}))
        self.opportunity = PaperOpportunityEngine(config.get("opportunity", {}))
        self.market_states = MarketStateStore(config.get("opportunity", {}).get("data_dir", "PC_ENGINE/data/radar"))
        self.exchanges = self._build_exchanges()
        self.paper_collector: PaperMarketCollector | None = None
        self._build_paper_collector()
        self.thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.lock = threading.RLock()
        self.cycle_count = 0
        self.preflight_done = False
        self._load_recovery_state()

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

    def _build_paper_collector(self) -> None:
        radar_cfg = self.config.get("radar", {})
        enabled = bool(radar_cfg.get("enabled", True)) and bool(radar_cfg.get("observational_only", True))
        if not self.paper or not enabled:
            self.paper_collector = None
            return
        collector_cfg = dict(radar_cfg)
        collector_cfg["confluence"] = self.config.get("confluence", {})
        collector_cfg["candlestick"] = self.config.get("candlestick", {})
        collector_cfg["timeframe"] = self.config.get("strategy", {}).get("timeframe", "1m")
        collector_cfg["candles_limit"] = self.config.get("strategy", {}).get("candles_limit", 120)
        collector_cfg["data_dir"] = self.config.get("confluence", {}).get("data_dir", "PC_ENGINE/data/radar")
        self.paper_collector = PaperMarketCollector(
            settings=collector_cfg,
            symbols=self.config.get("symbols", []),
            ohlcv_fetcher=self._fetch_ohlcv_for_collector,
            strategy=self.strategy,
            on_error=self.log,
        )

    def _fetch_ohlcv_for_collector(self, symbol: str, timeframe: str, limit: int) -> list[list[float]]:
        exchange = self._main_exchange()
        if exchange is None:
            return []
        return exchange.fetch_ohlcv(symbol, timeframe, limit)

    def _load_recovery_state(self) -> None:
        raw_positions = self.recovery.load_positions()
        recovered = {}
        for symbol, data in raw_positions.items():
            try:
                recovered[symbol] = Position(**data)
            except Exception:
                continue
        if recovered:
            self.state.open_positions.update(recovered)
            self.log("RECOVERY_POSITIONS_LOADED", {"symbols": list(recovered.keys())})

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
        preflight = self.run_preflight()
        if self.config.get("engine", {}).get("preflight_required", True) and not preflight["ok"]:
            self.state.status = "SAFE_MODE"
            self.log("PREFLIGHT_BLOCKED_START", preflight)
            return
        self.stop_event.clear()
        self.state.status = "RUNNING"
        if self.paper and self.paper_collector is not None:
            self.paper_collector.start()
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()
        self.log("ENGINE_STARTED", {"mode": self.mode})

    def run_preflight(self) -> dict:
        runtime_config = dict(self.config)
        runtime_config["mode"] = self.mode
        checker = PreflightChecker(runtime_config, self.rules)
        result = checker.run(self.exchanges)
        payload = {"ok": result.ok, "errors": result.errors, "warnings": result.warnings}
        with self.lock:
            self.state.preflight = payload
        self.preflight_done = result.ok
        self.log("PREFLIGHT_DONE", payload)
        return payload

    def pause(self, paused: bool = True) -> None:
        with self.lock:
            self.state.status = "PAUSED" if paused else "RUNNING"
        self.log("ENGINE_PAUSED" if paused else "ENGINE_RESUMED")

    def stop(self) -> None:
        self.stop_event.set()
        if self.paper_collector is not None:
            self.paper_collector.stop()
        with self.lock:
            self.state.status = "OFF"
            self.state.paper_collector = self.paper_collector.snapshot() if self.paper_collector else {"running": False}
        self.recovery.save_positions(self.state.open_positions)
        self.log("ENGINE_STOPPED")

    def set_mode(self, mode: str) -> None:
        mode = mode.upper()
        if mode not in {"PAPER", "REAL"}:
            raise ValueError("mode must be PAPER or REAL")
        if mode == "REAL" and self.state.status == "RUNNING":
            raise RuntimeError("Stop the engine before switching to REAL")
        if mode == "REAL" and self.paper_collector is not None:
            self.paper_collector.stop()
        self.mode = mode
        self.paper = mode != "REAL"
        self.state.mode = mode
        self.exchanges = self._build_exchanges()
        if self.paper:
            self._build_paper_collector()
        else:
            self.paper_collector = None
        self.log("MODE_CHANGED", {"mode": mode})

    def snapshot(self) -> dict:
        with self.lock:
            data = asdict(self.state)
            data["open_positions"] = {k: asdict(v) for k, v in self.state.open_positions.items()}
            data["paper_collector"] = self.paper_collector.snapshot() if self.paper_collector else {"running": False}
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
                self.recovery.save_positions(self.state.open_positions)
                time.sleep(15)
                self.state.status = "RUNNING"
            time.sleep(float(self.config["engine"].get("cycle_seconds", 20)))

    def _watchdog_gate(self, exchange: CcxtExchangeClient) -> bool:
        self.cycle_count += 1
        interval = int(self.config.get("watchdog", {}).get("internet_check_interval_cycles", 3))
        if self.config.get("watchdog", {}).get("enabled", True) and self.cycle_count % max(1, interval) == 0:
            status = self.watchdog.check_internet()
            self.state.watchdog = asdict(status)
            if not status.ok:
                self.state.status = "SAFE_MODE"
                self.log("WATCHDOG_BLOCK", asdict(status))
                return False
            symbol = self.config["symbols"][0]
            ex_status = self.watchdog.check_exchange(exchange, symbol)
            self.state.watchdog = asdict(ex_status)
            if not ex_status.ok:
                self.state.status = "SAFE_MODE"
                self.log("WATCHDOG_EXCHANGE_BLOCK", asdict(ex_status))
                return False
        return True

    def cycle(self) -> None:
        exchange = self._main_exchange()
        if exchange is None:
            self.log("NO_EXCHANGE_ENABLED")
            return
        if not self._watchdog_gate(exchange):
            return
        if self.state.status == "SAFE_MODE":
            self.state.status = "RUNNING"

        balance = exchange.free_quote_balance(self.config["engine"].get("quote_currency", "USDT"))
        if self.paper:
            balance = float(self.config["engine"].get("paper_starting_balance", 1000.0)) + self.risk.state.pnl_today_pct * float(self.config["engine"].get("paper_starting_balance", 1000.0))
        equity = balance
        with self.lock:
            self.state.balance = balance
            self.state.equity = equity
        self.risk.update_equity(equity, float(self.config["engine"].get("paper_starting_balance", equity)))
        global_ok, global_reason = self.risk.can_trade_global()
        if not global_ok:
            self.state.status = "KILL_SWITCH"
            self.recovery.save_positions(self.state.open_positions)
            self.log("GLOBAL_RISK_BLOCK", {"reason": global_reason})
            return

        scores: dict[str, float] = {}
        signals = {}
        spreads: dict[str, float] = {}
        for symbol in self.config["symbols"]:
            try:
                ohlcv = exchange.fetch_ohlcv(symbol, self.config["strategy"]["timeframe"], int(self.config["strategy"]["candles_limit"]))
                spread_pct = exchange.fetch_spread_pct(symbol)
                spreads[symbol] = spread_pct
                signal = self.strategy.analyse(symbol, ohlcv, spread_pct)
                signals[symbol] = signal
                market_state = self.market_states.snapshot(symbol) if self.paper else None
                opportunity = self.opportunity.score(
                    symbol=symbol,
                    strategy_score=float(signal.strength),
                    action=str(signal.action),
                    spread_pct=spread_pct,
                    state=market_state,
                )
                score = opportunity.score * 100.0
                opinion = self.ai_council.analyse(symbol, {"signal": asdict(signal), "opportunity": asdict(opportunity)})
                max_delta = float(self.config.get("ai_council", {}).get("max_score_delta", 5.0))
                score += max(-max_delta, min(max_delta, opinion.score_delta))
                scores[symbol] = max(0.0, score)
                self.state.regimes[symbol] = signal.regime
                with self.lock:
                    self.state.opportunities[symbol] = asdict(opportunity)
            except Exception as exc:
                scores[symbol] = 0.0
                self.log("SYMBOL_ANALYSIS_ERROR", {"symbol": symbol, "error": str(exc)})

        allocations = self.allocator.allocate(equity, scores)
        with self.lock:
            self.state.asset_scores = scores
            self.state.drawdown_pct = self.risk.state.drawdown_pct
            self.state.pnl_today_pct = self.risk.state.pnl_today_pct
            self.state.pnl_week_pct = self.risk.state.pnl_week_pct
            self.state.champion_challenger = self.champion.recommendation()

        for symbol, position in list(self.state.open_positions.items()):
            ticker = exchange.fetch_ticker(symbol)
            price = float(ticker.get("last") or 0.0)
            signal = signals.get(symbol)
            if price <= position.stop or price >= position.take_profit or (signal and signal.action == "SELL"):
                self._close_position(exchange, position, price, signal.reason if signal else "stop/take-profit", spreads.get(symbol, 0.0))

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
            self._open_position(exchange, symbol, price, qty, signal.stop_pct, signal.take_profit_pct, signal.reason, spreads.get(symbol, 0.0))

        self.recovery.save_positions(self.state.open_positions)

    def _open_position(self, exchange: CcxtExchangeClient, symbol: str, price: float, qty: float, stop_pct: float, tp_pct: float, reason: str, spread_pct: float = 0.0) -> None:
        result = self.order_manager.buy(exchange, symbol, qty, price, self.paper, spread_pct)
        if not result.ok:
            self.log("ORDER_REJECTED", {"symbol": symbol, "side": "buy", "reason": result.reason})
            return
        position = Position(
            exchange=exchange.name,
            symbol=symbol,
            entry=result.price,
            qty=result.qty,
            stop=result.price * (1 - stop_pct),
            take_profit=result.price * (1 + tp_pct),
            opened_ts=time.time(),
            entry_fee=result.fee,
        )
        with self.lock:
            self.state.open_positions[symbol] = position
        self.log("POSITION_OPENED", {"symbol": symbol, "price": result.price, "qty": result.qty, "fee": result.fee, "reason": reason})

    def _close_position(self, exchange: CcxtExchangeClient, position: Position, price: float, reason: str, spread_pct: float = 0.0) -> None:
        result = self.order_manager.sell(exchange, position.symbol, position.qty, price, self.paper, spread_pct)
        if not result.ok:
            self.log("ORDER_REJECTED", {"symbol": position.symbol, "side": "sell", "reason": result.reason})
            return
        pnl_pct = (result.price - position.entry) / position.entry if position.entry else 0.0
        notional = result.price * position.qty
        fee_pct_equiv = (position.entry_fee + result.fee) / notional if notional > 0 else 0.0
        pnl_pct -= fee_pct_equiv
        self.risk.record_trade_result(position.symbol, pnl_pct)
        self.champion.record("trend_ema_atr", pnl_pct, self.risk.state.drawdown_pct, live=True)
        with self.lock:
            self.state.open_positions.pop(position.symbol, None)
        self.ledger.trade({
            "exchange": position.exchange,
            "symbol": position.symbol,
            "side": "close",
            "qty": position.qty,
            "entry": position.entry,
            "exit": result.price,
            "fees": position.entry_fee + result.fee,
            "pnl_pct": pnl_pct,
            "reason": reason,
        })
        self.log("POSITION_CLOSED", {"symbol": position.symbol, "pnl_pct": pnl_pct, "fee": position.entry_fee + result.fee, "reason": reason})
