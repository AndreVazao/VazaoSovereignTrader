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
from PC_ENGINE.research.autonomous import AutonomousResearchWorker
from PC_ENGINE.research.worker import ResearchWorker


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
    account_reconciliation: Dict[str, object] = field(default_factory=dict)
    champion_challenger: Dict[str, object] = field(default_factory=dict)
    paper_collector: Dict[str, object] = field(default_factory=dict)
    research: Dict[str, object] = field(default_factory=dict)
    pending_orders: Dict[str, dict] = field(default_factory=dict)
    execution_intents: Dict[str, dict] = field(default_factory=dict)
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
        research_dir = config.get("research", {}).get("data_dir", "PC_ENGINE/data/research")
        research_cfg = config.get("research", {})
        self.autonomous_research = AutonomousResearchWorker(
            research_dir,
            min_observation_score=float(research_cfg.get("min_observation_score", 70.0)),
            dedupe_seconds=float(research_cfg.get("dedupe_seconds", 3600.0)),
        )
        self.research_worker = ResearchWorker(
            research_dir,
            replay_path=str(research_cfg.get("replay_path", "PC_ENGINE/data/replay/l2_temporal_replay.json")),
            oos_path=str(research_cfg.get("oos_path", "PC_ENGINE/data/radar/l2_oos_validation.json")),
        )
        self.research_stop_event = threading.Event()
        self.research_thread: Optional[threading.Thread] = None
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
        raw_state = self.recovery.load_state()
        raw_positions = raw_state.get("positions", {})
        pending = raw_state.get("pending_orders", {})
        intents = raw_state.get("execution_intents", {})
        self.state.pending_orders.update(pending)
        self.state.execution_intents.update(intents)
        self.order_manager.restore_order_guards(raw_state.get("order_guards", {}))
        if pending:
            self.state.status = "SAFE_MODE"
            self.log("RECOVERY_PENDING_ORDERS", {"order_ids": list(pending)})
        if intents:
            self.state.status = "SAFE_MODE"
            self.log("RECOVERY_UNRESOLVED_EXECUTION_INTENTS", {"intent_ids": list(intents)})
        recovered = {}
        for symbol, data in raw_positions.items():
            try:
                recovered[symbol] = Position(**data)
            except Exception:
                continue
        if recovered:
            self.state.open_positions.update(recovered)
            self.log("RECOVERY_POSITIONS_LOADED", {"symbols": list(recovered.keys())})

    def _persist_recovery(self) -> None:
        self.recovery.save_positions(self.state.open_positions, self.state.pending_orders, self.order_manager.export_order_guards(), self.state.execution_intents)

    def reconcile_account_state(self) -> dict:
        """Verify local positions and open orders against the live exchange."""
        exchange = self._main_exchange()
        if exchange is None:
            result = {"ok": False, "status": "BLOCKED", "reason": "no_exchange"}
            self.state.account_reconciliation = result
            return result
        if self.paper:
            result = {"ok": True, "status": "PAPER", "tracked_positions": len(self.state.open_positions), "open_orders": 0}
            self.state.account_reconciliation = result
            return result
        try:
            balance = exchange.fetch_balance()
            open_orders = exchange.fetch_open_orders()
            total = balance.get("total", {}) or {}
            quote = str(self.config.get("engine", {}).get("quote_currency", "USDT"))
            mismatches = []
            tracked_assets = set()
            for symbol, position in self.state.open_positions.items():
                base_asset = str(symbol).split("/", 1)[0]
                tracked_assets.add(base_asset)
                exchange_qty = float(total.get(base_asset, 0.0) or 0.0)
                tolerance = max(1e-12, abs(float(position.qty)) * 0.001)
                if abs(exchange_qty - float(position.qty)) > tolerance:
                    mismatches.append({"symbol": symbol, "asset": base_asset, "local_qty": float(position.qty), "exchange_total": exchange_qty, "tolerance": tolerance})
            unexpected_assets = []
            for asset, value in total.items():
                qty = float(value or 0.0)
                if qty > 1e-10 and str(asset) not in tracked_assets and str(asset) != quote:
                    unexpected_assets.append({"asset": str(asset), "total": qty})
            result = {
                "ok": not mismatches and not unexpected_assets and not open_orders,
                "status": "MATCH" if not mismatches and not unexpected_assets and not open_orders else "BLOCKED",
                "tracked_positions": len(self.state.open_positions),
                "open_orders": len(open_orders),
                "mismatches": mismatches,
                "unexpected_assets": unexpected_assets,
                "open_order_ids": [str(o.get("id", "")) for o in open_orders if o.get("id")],
                "checked_at": time.time(),
            }
        except NotImplementedError as exc:
            result = {"ok": False, "status": "BLOCKED", "reason": str(exc)}
        except Exception as exc:
            result = {"ok": False, "status": "ERROR", "reason": str(exc)}
        self.state.account_reconciliation = result
        if not result.get("ok"):
            self.state.status = "SAFE_MODE"
            self.log("ACCOUNT_RECONCILIATION_BLOCKED", result)
        else:
            self.log("ACCOUNT_RECONCILIATION_MATCH", result)
        return result

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
        self.research_stop_event.clear()
        self.state.status = "RUNNING"
        if self.config.get("research", {}).get("enabled", True):
            interval = float(self.config.get("research", {}).get("worker_interval_seconds", 2.0))
            self.research_thread = threading.Thread(
                target=self.research_worker.run_forever,
                args=(self.research_stop_event, interval),
                name="research-worker",
                daemon=True,
            )
            self.research_thread.start()
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
        self.research_stop_event.set()
        if self.paper_collector is not None:
            self.paper_collector.stop()
        if self.research_thread is not None and self.research_thread.is_alive():
            self.research_thread.join(timeout=1.0)
        with self.lock:
            self.state.status = "OFF"
            self.state.paper_collector = self.paper_collector.snapshot() if self.paper_collector else {"running": False}
        self._persist_recovery()
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
                self._persist_recovery()
                time.sleep(15)
                continue
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

    def _reconcile_pending_orders(self) -> None:
        """Reconcile final exchange fills without guessing unknown positions."""
        exchange = self._main_exchange()
        if exchange is None:
            return
        for order_id, item in list(self.state.pending_orders.items()):
            symbol = str(item.get("symbol", ""))
            if not order_id or not symbol:
                continue
            try:
                raw = exchange.fetch_order(order_id, symbol)
                status = str(raw.get("status") or "").lower()
                if status in {"open", "new", "partially_filled", "partially-filled"}:
                    self.log("PENDING_ORDER_STILL_OPEN", {"order_id": order_id, "symbol": symbol, "status": status, "filled_qty": raw.get("filled")})
                    continue
                if status not in {"closed", "filled", "canceled", "cancelled", "rejected"}:
                    self.log("PENDING_ORDER_UNKNOWN_STATUS", {"order_id": order_id, "symbol": symbol, "status": status})
                    continue

                final_filled = float(raw.get("filled") or 0.0)
                known_filled = float(item.get("known_filled_qty") or 0.0)
                delta = max(0.0, final_filled - known_filled)
                side = str(item.get("side", "")).lower()

                if delta > 1e-12:
                    position = self.state.open_positions.get(symbol)
                    fill_price = float(raw.get("average") or raw.get("price") or item.get("known_fill_price") or 0.0)
                    if position is None or fill_price <= 0:
                        self.state.status = "SAFE_MODE"
                        self.log("MANUAL_RECONCILIATION_REQUIRED", {
                            "order_id": order_id, "symbol": symbol, "side": side,
                            "known_filled_qty": known_filled, "final_filled_qty": final_filled,
                            "delta_qty": delta,
                        })
                        continue

                    fee_raw = raw.get("fee", 0.0)
                    if isinstance(fee_raw, dict):
                        fee_value = float(fee_raw.get("cost") or fee_raw.get("amount") or 0.0)
                    else:
                        fee_value = float(fee_raw or 0.0)
                    if side == "buy":
                        old_qty = position.qty
                        old_cost = position.entry * old_qty
                        position.qty = old_qty + delta
                        position.entry = (old_cost + fill_price * delta) / position.qty
                        position.entry_fee += fee_value
                    elif side == "sell":
                        if delta > position.qty + 1e-12:
                            self.state.status = "SAFE_MODE"
                            self.log("MANUAL_RECONCILIATION_REQUIRED", {
                                "order_id": order_id, "symbol": symbol, "side": side,
                                "position_qty": position.qty, "delta_qty": delta,
                            })
                            continue
                        allocated_entry_fee = position.entry_fee * (delta / position.qty) if position.qty > 0 else 0.0
                        gross_pnl = (fill_price - position.entry) * delta
                        sell_fee = fee_value
                        net_pnl = gross_pnl - allocated_entry_fee - sell_fee
                        pnl_pct = net_pnl / (position.entry * delta) if position.entry > 0 and delta > 0 else 0.0
                        self.risk.record_trade_result(symbol, pnl_pct)
                        self.champion.record("trend_ema_atr", pnl_pct, self.risk.state.drawdown_pct, live=True)
                        position.qty -= delta
                        position.entry_fee = max(0.0, position.entry_fee - allocated_entry_fee)
                        self.ledger.trade({
                            "exchange": position.exchange,
                            "symbol": symbol,
                            "side": "close",
                            "qty": delta,
                            "entry": position.entry,
                            "exit": fill_price,
                            "fees": allocated_entry_fee + sell_fee,
                            "pnl_pct": pnl_pct,
                            "reason": "reconciled_pending_order",
                        })
                        if position.qty <= 1e-12:
                            self.state.open_positions.pop(symbol, None)
                    else:
                        self.state.status = "SAFE_MODE"
                        self.log("MANUAL_RECONCILIATION_REQUIRED", {"order_id": order_id, "symbol": symbol, "reason": "unknown_side"})
                        continue

                self.log("PENDING_ORDER_RECONCILED", {
                    "order_id": order_id,
                    "symbol": symbol,
                    "side": side,
                    "status": status,
                    "known_filled_qty": known_filled,
                    "final_filled_qty": final_filled,
                    "delta_qty": delta,
                })
                self.state.pending_orders.pop(order_id, None)
                self._persist_recovery()
            except Exception as exc:
                self.state.status = "SAFE_MODE"
                self.log("PENDING_ORDER_RECONCILE_ERROR", {"order_id": order_id, "symbol": symbol, "error": str(exc)})
        if self.state.pending_orders:
            self.state.status = "SAFE_MODE"

    def cycle(self) -> None:
        exchange = self._main_exchange()
        if exchange is None:
            self.log("NO_EXCHANGE_ENABLED")
            return
        if not self._watchdog_gate(exchange):
            return
        if self.mode == "REAL" and not self.state.account_reconciliation.get("ok", False):
            self.reconcile_account_state()
            return
        if self.state.pending_orders:
            self._reconcile_pending_orders()
            return
        if self.state.status == "SAFE_MODE":
            self.log("SAFE_MODE_HOLD")
            return

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
            self._persist_recovery()
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
                if self.config.get("research", {}).get("enabled", True) and self.config.get("research", {}).get("autonomous_observation_enabled", True):
                    self.autonomous_research.observe(symbol, score, signal.regime, asdict(opportunity))
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
            self.state.research = {
                **self.autonomous_research.snapshot(),
                "inbox": self.research_worker.inbox.snapshot(),
            }

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

        self._persist_recovery()

    def _open_position(self, exchange: CcxtExchangeClient, symbol: str, price: float, qty: float, stop_pct: float, tp_pct: float, reason: str, spread_pct: float = 0.0) -> None:
        intent_id = f"intent-{time.time_ns()}"
        self.state.execution_intents[intent_id] = {
            "exchange": exchange.name, "symbol": symbol, "side": "buy",
            "requested_qty": float(qty), "reference_price": float(price),
            "created_ts": time.time(),
        }
        self._persist_recovery()
        try:
            result = self.order_manager.buy(exchange, symbol, qty, price, self.paper, spread_pct)
        except Exception:
            self.state.status = "SAFE_MODE"
            self._persist_recovery()
            raise
        self.state.execution_intents.pop(intent_id, None)
        self._persist_recovery()
        if result.status == "PENDING_OR_PARTIAL":
            self.state.status = "SAFE_MODE"
            self.log("ORDER_FILL_UNCONFIRMED", {
                "symbol": symbol,
                "side": "buy",
                "order_id": result.order_id,
                "filled_qty": result.qty,
                "requested_qty": result.requested_qty,
                "reason": result.reason,
            })
            if not result.order_id:
                self.log("ORDER_RECONCILIATION_REQUIRED", {"symbol": symbol, "side": "buy", "reason": "missing_order_id"})
                return
            self.state.pending_orders[result.order_id] = {
                "exchange": exchange.name,
                "symbol": symbol,
                "side": "buy",
                "requested_qty": result.requested_qty,
                "known_filled_qty": result.qty,
                "known_fill_price": result.price,
                "known_fee": result.fee,
                "created_ts": time.time(),
            }
            self._persist_recovery()
            if result.qty <= 0:
                return
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
        intent_id = f"intent-{time.time_ns()}"
        self.state.execution_intents[intent_id] = {
            "exchange": exchange.name, "symbol": position.symbol, "side": "sell",
            "requested_qty": float(position.qty), "reference_price": float(price),
            "created_ts": time.time(),
        }
        self._persist_recovery()
        try:
            result = self.order_manager.sell(exchange, position.symbol, position.qty, price, self.paper, spread_pct)
        except Exception:
            self.state.status = "SAFE_MODE"
            self._persist_recovery()
            raise
        self.state.execution_intents.pop(intent_id, None)
        self._persist_recovery()
        if result.status == "PENDING_OR_PARTIAL":
            self.state.status = "SAFE_MODE"
            self.log("EXIT_FILL_UNCONFIRMED", {
                "symbol": position.symbol,
                "side": "sell",
                "order_id": result.order_id,
                "filled_qty": result.qty,
                "requested_qty": result.requested_qty,
                "reason": result.reason,
            })
            if not result.order_id:
                self.log("ORDER_RECONCILIATION_REQUIRED", {"symbol": position.symbol, "side": "sell", "reason": "missing_order_id"})
                return
            self.state.pending_orders[result.order_id] = {
                "exchange": exchange.name,
                "symbol": position.symbol,
                "side": "sell",
                "requested_qty": result.requested_qty,
                "known_filled_qty": result.qty,
                "known_fill_price": result.price,
                "known_fee": result.fee,
                "created_ts": time.time(),
            }
            self._persist_recovery()
            if result.qty <= 0:
                return
        if not result.ok:
            self.log("ORDER_REJECTED", {"symbol": position.symbol, "side": "sell", "reason": result.reason})
            return
        filled_qty = min(float(result.qty), float(position.qty))
        if filled_qty <= 0:
            return
        allocated_entry_fee = position.entry_fee * (filled_qty / position.qty) if position.qty > 0 else 0.0
        notional = result.price * filled_qty
        gross_pnl = (result.price - position.entry) * filled_qty
        net_pnl = gross_pnl - allocated_entry_fee - result.fee
        pnl_pct = net_pnl / (position.entry * filled_qty) if position.entry and filled_qty > 0 else 0.0
        self.risk.record_trade_result(position.symbol, pnl_pct)
        self.champion.record("trend_ema_atr", pnl_pct, self.risk.state.drawdown_pct, live=True)
        remaining_qty = max(0.0, position.qty - filled_qty)
        with self.lock:
            if remaining_qty <= 1e-12:
                self.state.open_positions.pop(position.symbol, None)
            else:
                position.qty = remaining_qty
                position.entry_fee = max(0.0, position.entry_fee - allocated_entry_fee)
        self.ledger.trade({
            "exchange": position.exchange,
            "symbol": position.symbol,
            "side": "close",
            "qty": filled_qty,
            "entry": position.entry,
            "exit": result.price,
            "fees": allocated_entry_fee + result.fee,
            "pnl_pct": pnl_pct,
            "reason": reason,
        })
        self.log("POSITION_PARTIALLY_CLOSED" if remaining_qty > 1e-12 else "POSITION_CLOSED", {
            "symbol": position.symbol,
            "filled_qty": filled_qty,
            "remaining_qty": remaining_qty,
            "pnl_pct": pnl_pct,
            "fee": allocated_entry_fee + result.fee,
            "reason": reason,
        })
