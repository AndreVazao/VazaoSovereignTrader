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
    financial_reconciliation: Dict[str, object] = field(default_factory=dict)
    financial_account: Dict[str, object] = field(default_factory=dict)
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
        financial_account = raw_state.get("financial_account", {})
        if isinstance(financial_account, dict):
            self.state.financial_account.update(financial_account)
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
        self.recovery.save_positions(self.state.open_positions, self.state.pending_orders, self.order_manager.export_order_guards(), self.state.execution_intents, self.state.financial_account)

    def reconcile_account_state(self) -> dict:
        """Verify local positions, balances, and open orders against the live exchange."""
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
            recon_cfg = self.config.get("reconciliation", {})
            dust_tolerance = max(0.0, float(recon_cfg.get("dust_tolerance", 1e-10)))
            relative_tolerance = max(0.0, float(recon_cfg.get("relative_tolerance", 0.001)))
            financial_tolerance = max(0.0, float(recon_cfg.get("financial_relative_tolerance", 0.002)))
            financial = self.state.financial_account
            baseline = financial.get("baseline_total")
            quote_flow = float(financial.get("quote_flow", 0.0) or 0.0)

            expected_by_asset: dict[str, float] = {}
            symbols_by_asset: dict[str, list[str]] = {}
            for symbol, position in self.state.open_positions.items():
                base_asset = str(symbol).split("/", 1)[0]
                expected_by_asset[base_asset] = expected_by_asset.get(base_asset, 0.0) + float(position.qty)
                symbols_by_asset.setdefault(base_asset, []).append(symbol)

            if baseline is None:
                baseline = {str(k): float(v or 0.0) for k, v in total.items() if str(k) == quote or str(k) in expected_by_asset}
                financial["baseline_total"] = baseline
                financial["quote_flow"] = quote_flow
                financial["initialized_at"] = time.time()
                self.log("FINANCIAL_ACCOUNT_BASELINE_INITIALIZED", {"baseline_total": baseline})
            baseline_quote = float(baseline.get(quote, 0.0) or 0.0)
            expected_quote = baseline_quote + quote_flow
            exchange_quote = float(total.get(quote, 0.0) or 0.0)
            quote_tol = max(dust_tolerance, abs(expected_quote) * financial_tolerance)
            quote_mismatch = abs(exchange_quote - expected_quote) > quote_tol
            mismatches = []
            for asset, expected_qty in expected_by_asset.items():
                exchange_qty = float(total.get(asset, 0.0) or 0.0)
                tolerance = max(dust_tolerance, abs(expected_qty) * relative_tolerance)
                if abs(exchange_qty - expected_qty) > tolerance:
                    mismatches.append({
                        "asset": asset,
                        "symbols": symbols_by_asset.get(asset, []),
                        "local_qty": expected_qty,
                        "exchange_total": exchange_qty,
                        "tolerance": tolerance,
                    })

            unexpected_assets = []
            for asset, value in total.items():
                asset_name = str(asset)
                qty = float(value or 0.0)
                if asset_name == quote or qty <= dust_tolerance:
                    continue
                if asset_name not in expected_by_asset:
                    unexpected_assets.append({
                        "asset": asset_name,
                        "total": qty,
                        "reason": "exchange_asset_without_local_position",
                    })

            result = {
                "ok": not mismatches and not unexpected_assets and not open_orders and not quote_mismatch,
                "status": "MATCH" if not mismatches and not unexpected_assets and not open_orders else "BLOCKED",
                "tracked_positions": len(self.state.open_positions),
                "expected_assets": expected_by_asset,
                "open_orders": len(open_orders),
                "mismatches": mismatches,
                "unexpected_assets": unexpected_assets,
                "open_order_ids": [str(o.get("id", "")) for o in open_orders if o.get("id")],
                "dust_tolerance": dust_tolerance,
                "relative_tolerance": relative_tolerance,
                "financial_account": dict(financial),
                "quote_mismatch": quote_mismatch,
                "expected_quote": expected_quote,
                "exchange_quote": exchange_quote,
                "quote_tolerance": quote_tol,
                "checked_at": time.time(),
            }
        except (NotImplementedError, ValueError, TypeError) as exc:
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
        if self.state.execution_intents:
            self._recover_unresolved_execution_intents()
            if self.state.execution_intents:
                self.state.status = "SAFE_MODE"
                self.log("RECOVERY_UNRESOLVED_EXECUTION_INTENTS_BLOCK_START", {"intent_ids": list(self.state.execution_intents)})
                return
        # In REAL mode, reconcile the live account before exposing RUNNING state.
        # Recovery must happen first so an unambiguous open order can be converted
        # into a pending order; reconciliation then deliberately blocks while that
        # order is unresolved. This prevents even a brief startup window where REAL
        # execution is active against an unreconciled account.
        if self.mode == "REAL":
            reconciliation = self.reconcile_account_state()
            if not reconciliation.get("ok", False):
                self.state.status = "SAFE_MODE"
                self.log("REAL_START_BLOCKED_ACCOUNT_RECONCILIATION", reconciliation)
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

    def _recover_unresolved_execution_intents(self) -> None:
        """Find only unambiguously matching open orders after a crash.

        This never assumes a fill. If no unique open-order match exists, the
        intent remains unresolved and startup stays in SAFE_MODE.
        """
        if not self.state.execution_intents or self.paper:
            return
        exchange = self._main_exchange()
        if exchange is None:
            return
        try:
            open_orders = exchange.fetch_open_orders()
        except Exception as exc:
            self.log("EXECUTION_INTENT_RECOVERY_BLOCKED", {"error": str(exc)})
            return
        for intent_id, intent in list(self.state.execution_intents.items()):
            symbol = str(intent.get("symbol", ""))
            side = str(intent.get("side", "")).lower()
            requested = float(intent.get("requested_qty") or 0.0)
            if not symbol or side not in {"buy", "sell"} or requested <= 0:
                continue
            client_order_id = str(intent.get("client_order_id") or "").strip()
            matches = []
            if client_order_id:
                for order in open_orders:
                    exchange_client_id = str(order.get("clientOrderId") or order.get("client_order_id") or "").strip()
                    if exchange_client_id == client_order_id and order.get("id"):
                        matches.append(order)
                if len(matches) != 1:
                    try:
                        historical = exchange.fetch_order_by_client_order_id(client_order_id, symbol)
                    except (NotImplementedError, LookupError) as exc:
                        self.log("EXECUTION_INTENT_CLOSED_LOOKUP_UNAVAILABLE", {
                            "intent_id": intent_id, "client_order_id": client_order_id, "reason": str(exc)
                        })
                        historical = None
                    except Exception as exc:
                        self.log("EXECUTION_INTENT_CLOSED_LOOKUP_ERROR", {
                            "intent_id": intent_id, "client_order_id": client_order_id, "error": str(exc)
                        })
                        historical = None
                    if historical and historical.get("id"):
                        self.state.pending_orders[str(historical["id"])] = {
                            "exchange": exchange.name,
                            "symbol": symbol,
                            "side": side,
                            "requested_qty": requested,
                            "known_filled_qty": 0.0,
                            "known_fill_price": float(intent.get("reference_price") or 0.0),
                            "known_fee": 0.0,
                            "known_quote_notional": 0.0,
                            "created_ts": float(intent.get("created_ts") or time.time()),
                            "recovered_from_intent": intent_id,
                            "client_order_id": client_order_id,
                            "stop_pct": float(intent.get("stop_pct") or 0.0),
                            "take_profit_pct": float(intent.get("take_profit_pct") or 0.0),
                            "reason": str(intent.get("reason") or "recovered_execution_intent"),
                        }
                        self.state.execution_intents.pop(intent_id, None)
                        self.log("EXECUTION_INTENT_RECOVERED_HISTORICAL_ORDER", {
                            "intent_id": intent_id, "order_id": str(historical["id"]), "symbol": symbol, "side": side
                        })
                    continue
            else:
                for order in open_orders:
                    if str(order.get("symbol", "")) != symbol:
                        continue
                    if str(order.get("side", "")).lower() != side:
                        continue
                    amount = float(order.get("amount") or order.get("origQty") or 0.0)
                    if amount <= 0 or abs(amount - requested) > max(1e-12, requested * 1e-9):
                        continue
                    if order.get("id"):
                        matches.append(order)
                if len(matches) != 1:
                    continue
            order = matches[0]
            order_id = str(order["id"])
            # The recovered order has not had any fill applied locally yet.
            self.state.pending_orders[order_id] = {
                "exchange": exchange.name,
                "symbol": symbol,
                "side": side,
                "requested_qty": requested,
                "known_filled_qty": 0.0,
                "known_fill_price": float(order.get("average") or order.get("price") or intent.get("reference_price") or 0.0),
                "known_fee": 0.0,
                "known_quote_notional": 0.0,
                "created_ts": float(intent.get("created_ts") or time.time()),
                "recovered_from_intent": intent_id,
                "client_order_id": client_order_id,
                "stop_pct": float(intent.get("stop_pct") or 0.0),
                "take_profit_pct": float(intent.get("take_profit_pct") or 0.0),
                "reason": str(intent.get("reason") or "recovered_execution_intent"),
            }
            self.state.execution_intents.pop(intent_id, None)
            self.log("EXECUTION_INTENT_RECOVERED_OPEN_ORDER", {"intent_id": intent_id, "order_id": order_id, "symbol": symbol, "side": side})
        self._persist_recovery()

    def _extract_cumulative_quote_fee(self, raw: dict, symbol: str) -> float:
        """Return cumulative fee only when safely quote-denominated."""
        fee_entries = raw.get("fees")
        if isinstance(fee_entries, list) and fee_entries:
            entries = fee_entries
        else:
            single = raw.get("fee")
            entries = [single] if isinstance(single, dict) else []
        if not entries:
            single = raw.get("fee")
            if single is None:
                return 0.0
            if isinstance(single, (int, float, str)):
                return max(0.0, float(single))
            return 0.0
        quote = str(symbol).split("/", 1)[1] if "/" in symbol else ""
        total = 0.0
        currencies = set()
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            currency = str(entry.get("currency") or "").strip()
            if currency:
                currencies.add(currency)
            cost = entry.get("cost")
            if cost is None:
                cost = entry.get("amount")
            if cost is not None:
                total += float(cost)
        if currencies and quote and any(currency != quote for currency in currencies):
            raise ValueError(f"non-quote fee currency for {symbol}: {sorted(currencies)}")
        return max(0.0, total)

    def _validate_order_financial_invariant(self, raw: dict, symbol: str, filled_qty: float, average_price: float) -> dict:
        """Validate exchange-reported quantity/price/cost consistency before accounting."""
        cfg = self.config.get("reconciliation", {})
        relative_tolerance = max(0.0, float(cfg.get("financial_relative_tolerance", 0.002)))
        cost = raw.get("cost")
        fee = raw.get("fee")
        if cost is None:
            cost_value = None
        else:
            cost_value = float(cost)
            if cost_value < 0:
                return {"ok": False, "reason": "negative_order_cost", "cost": cost_value}
        if average_price < 0 or filled_qty < 0:
            return {"ok": False, "reason": "negative_fill_or_price"}
        expected_cost = filled_qty * average_price
        if cost_value is not None:
            tolerance = max(1e-12, abs(expected_cost) * relative_tolerance)
            if abs(cost_value - expected_cost) > tolerance:
                return {
                    "ok": False,
                    "reason": "order_cost_price_quantity_mismatch",
                    "reported_cost": cost_value,
                    "expected_cost": expected_cost,
                    "tolerance": tolerance,
                }
        fee_value = 0.0
        if isinstance(fee, dict):
            fee_cost = fee.get("cost")
            if fee_cost is not None:
                fee_value = float(fee_cost)
        if fee_value < 0:
            return {"ok": False, "reason": "negative_fee", "fee": fee_value}
        return {
            "ok": True,
            "reported_cost": cost_value,
            "expected_cost": expected_cost,
            "fee": fee_value,
            "relative_tolerance": relative_tolerance,
        }

    def _reconcile_pending_orders(self) -> None:
        """Reconcile exchange fills idempotently, including partial fills and fees."""
        exchange = self._main_exchange()
        if exchange is None:
            return
        for order_id, item in list(self.state.pending_orders.items()):
            symbol = str(item.get("symbol", ""))
            if not order_id or not symbol:
                continue
            try:
                raw = exchange.fetch_order(order_id, symbol)
                expected_client_id = str(item.get("client_order_id") or "").strip()
                returned_client_id = str(raw.get("clientOrderId") or raw.get("client_order_id") or "").strip()
                if expected_client_id and returned_client_id != expected_client_id:
                    self.state.status = "SAFE_MODE"
                    self.log("PENDING_ORDER_IDENTITY_MISMATCH", {
                        "order_id": order_id,
                        "symbol": symbol,
                        "expected_client_order_id": expected_client_id,
                        "returned_client_order_id": returned_client_id,
                    })
                    continue

                status = str(raw.get("status") or "").lower()
                terminal = status in {"closed", "filled", "canceled", "cancelled", "rejected"}
                open_status = status in {"open", "new", "partially_filled", "partially-filled"}
                if not terminal and not open_status:
                    self.log("PENDING_ORDER_UNKNOWN_STATUS", {
                        "order_id": order_id, "symbol": symbol, "status": status
                    })
                    continue

                final_filled = float(raw.get("filled") or 0.0)
                known_filled = float(item.get("known_filled_qty") or 0.0)
                delta = max(0.0, final_filled - known_filled)
                side = str(item.get("side", "")).lower()
                financial = self._validate_order_financial_invariant(
                    raw, symbol, final_filled,
                    float(raw.get("average") or raw.get("price") or item.get("known_fill_price") or 0.0),
                )
                self.state.financial_reconciliation = {
                    "order_id": order_id,
                    "symbol": symbol,
                    **financial,
                    "checked_at": time.time(),
                }
                if not financial.get("ok", False):
                    self.state.status = "SAFE_MODE"
                    self.log("PENDING_ORDER_FINANCIAL_INVARIANT_BLOCKED", self.state.financial_reconciliation)
                    continue

                cumulative_fee = self._extract_cumulative_quote_fee(raw, symbol)
                known_fee = float(item.get("known_fee") or 0.0)
                if cumulative_fee + 1e-12 < known_fee:
                    self.state.status = "SAFE_MODE"
                    self.log("PENDING_ORDER_FEE_REGRESSION", {
                        "order_id": order_id, "symbol": symbol,
                        "known_fee": known_fee, "reported_fee": cumulative_fee,
                    })
                    continue
                fee_delta = max(0.0, cumulative_fee - known_fee)

                reported_cost = financial.get("reported_cost")
                cumulative_notional = (
                    float(reported_cost) if reported_cost is not None
                    else float(financial.get("expected_cost") or 0.0)
                )
                known_notional = float(item.get("known_quote_notional") or 0.0)
                notional_tolerance = max(1e-12, abs(cumulative_notional) * float(financial.get("relative_tolerance") or 0.002))
                if cumulative_notional + notional_tolerance < known_notional:
                    self.state.status = "SAFE_MODE"
                    self.log("PENDING_ORDER_NOTIONAL_REGRESSION", {
                        "order_id": order_id, "symbol": symbol,
                        "known_quote_notional": known_notional,
                        "reported_quote_notional": cumulative_notional,
                        "tolerance": notional_tolerance,
                    })
                    continue
                delta_notional = max(0.0, cumulative_notional - known_notional)

                if delta > 1e-12:
                    position = self.state.open_positions.get(symbol)
                    if delta_notional <= 0:
                        self.state.status = "SAFE_MODE"
                        self.log("PENDING_ORDER_MISSING_INCREMENTAL_NOTIONAL", {
                            "order_id": order_id, "symbol": symbol, "delta_qty": delta,
                            "delta_quote_notional": delta_notional,
                        })
                        continue
                    fill_price = delta_notional / delta
                    if fill_price <= 0:
                        self.state.status = "SAFE_MODE"
                        self.log("MANUAL_RECONCILIATION_REQUIRED", {
                            "order_id": order_id, "symbol": symbol, "side": side,
                            "known_filled_qty": known_filled, "final_filled_qty": final_filled,
                            "delta_qty": delta,
                        })
                        continue

                    if side == "buy":
                        if position is None:
                            stop_pct = float(item.get("stop_pct") or 0.0)
                            tp_pct = float(item.get("take_profit_pct") or 0.0)
                            if stop_pct <= 0 or tp_pct <= 0:
                                self.state.status = "SAFE_MODE"
                                self.log("MANUAL_RECONCILIATION_REQUIRED", {
                                    "order_id": order_id, "symbol": symbol,
                                    "reason": "missing_buy_recovery_risk_metadata",
                                })
                                continue
                            position = Position(
                                exchange=exchange.name, symbol=symbol, entry=fill_price, qty=delta,
                                stop=fill_price * (1 - stop_pct), take_profit=fill_price * (1 + tp_pct),
                                opened_ts=float(item.get("created_ts") or time.time()), entry_fee=fee_delta,
                            )
                            self.state.open_positions[symbol] = position
                            self.log("POSITION_RECOVERED_FROM_PENDING_BUY", {
                                "order_id": order_id, "symbol": symbol, "qty": delta, "entry": fill_price,
                            })
                        else:
                            old_qty = position.qty
                            old_cost = position.entry * old_qty
                            position.qty = old_qty + delta
                            position.entry = (old_cost + fill_price * delta) / position.qty
                            position.entry_fee += fee_delta
                    elif side == "sell":
                        if position is None or delta > position.qty + 1e-12:
                            self.state.status = "SAFE_MODE"
                            self.log("MANUAL_RECONCILIATION_REQUIRED", {
                                "order_id": order_id, "symbol": symbol, "side": side,
                                "position_qty": position.qty if position else 0.0, "delta_qty": delta,
                            })
                            continue
                        allocated_entry_fee = position.entry_fee * (delta / position.qty) if position.qty > 0 else 0.0
                        gross_pnl = (fill_price - position.entry) * delta
                        net_pnl = gross_pnl - allocated_entry_fee - fee_delta
                        pnl_pct = net_pnl / (position.entry * delta) if position.entry > 0 and delta > 0 else 0.0
                        self.risk.record_trade_result(symbol, pnl_pct)
                        self.champion.record("trend_ema_atr", pnl_pct, self.risk.state.drawdown_pct, live=True)
                        position.qty -= delta
                        position.entry_fee = max(0.0, position.entry_fee - allocated_entry_fee)
                        self.ledger.trade({
                            "exchange": position.exchange, "symbol": symbol, "side": "close", "qty": delta,
                            "entry": position.entry, "exit": fill_price,
                            "fees": allocated_entry_fee + fee_delta, "pnl_pct": pnl_pct,
                            "reason": "reconciled_pending_order",
                        })
                        if position.qty <= 1e-12:
                            self.state.open_positions.pop(symbol, None)
                    else:
                        self.state.status = "SAFE_MODE"
                        self.log("MANUAL_RECONCILIATION_REQUIRED", {
                            "order_id": order_id, "symbol": symbol, "reason": "unknown_side"
                        })
                        continue

                    if side == "buy":
                        self.state.financial_account["quote_flow"] = float(self.state.financial_account.get("quote_flow", 0.0) or 0.0) - delta_notional - fee_delta
                    elif side == "sell":
                        self.state.financial_account["quote_flow"] = float(self.state.financial_account.get("quote_flow", 0.0) or 0.0) + delta_notional - fee_delta

                item["known_filled_qty"] = final_filled
                item["known_fee"] = cumulative_fee
                item["known_quote_notional"] = cumulative_notional
                item["known_fill_price"] = float(
                    raw.get("average") or raw.get("price") or item.get("known_fill_price") or 0.0
                )
                self.log("PENDING_ORDER_RECONCILED", {
                    "order_id": order_id, "symbol": symbol, "side": side, "status": status,
                    "terminal": terminal, "known_filled_qty": known_filled,
                    "final_filled_qty": final_filled, "delta_qty": delta,
                    "known_fee": known_fee, "final_fee": cumulative_fee, "fee_delta": fee_delta,
                })
                # Persist the applied-fill marker atomically with the position.
                # If the process dies here, the next run sees the same pending
                # order but delta=0 and cannot apply the fill/fee a second time.
                self._persist_recovery()
                if terminal:
                    self.state.pending_orders.pop(order_id, None)
                    self._persist_recovery()
            except Exception as exc:
                self.state.status = "SAFE_MODE"
                self.log("PENDING_ORDER_RECONCILE_ERROR", {
                    "order_id": order_id, "symbol": symbol, "error": str(exc)
                })
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
        client_order_id = f"vzt-{time.time_ns()}-buy"
        self.state.execution_intents[intent_id] = {
            "exchange": exchange.name, "symbol": symbol, "side": "buy",
            "requested_qty": float(qty), "reference_price": float(price),
            "client_order_id": client_order_id,
            "stop_pct": float(stop_pct),
            "take_profit_pct": float(tp_pct),
            "reason": reason,
            "created_ts": time.time(),
        }
        self._persist_recovery()
        try:
            result = self.order_manager.buy(exchange, symbol, qty, price, self.paper, spread_pct, client_order_id)
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
                "client_order_id": client_order_id,
                "stop_pct": stop_pct,
                "take_profit_pct": tp_pct,
                "reason": reason,
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
        client_order_id = f"vzt-{time.time_ns()}-sell"
        self.state.execution_intents[intent_id] = {
            "exchange": exchange.name, "symbol": position.symbol, "side": "sell",
            "requested_qty": float(position.qty), "reference_price": float(price),
            "client_order_id": client_order_id,
            "reason": reason,
            "created_ts": time.time(),
        }
        self._persist_recovery()
        try:
            result = self.order_manager.sell(exchange, position.symbol, position.qty, price, self.paper, spread_pct, client_order_id)
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