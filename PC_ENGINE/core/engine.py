from __future__ import annotations

import math
import threading
import time
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional

from PC_ENGINE.ai_council.stub import DisabledAICouncil
from PC_ENGINE.core.allocator import CapitalAllocator
from PC_ENGINE.core.opportunity import PaperOpportunityEngine
from PC_ENGINE.core.config import DATA_DIR, env_value
from PC_ENGINE.core.owner_context import OwnerContext
from PC_ENGINE.core.exchange_rules import ExchangeRulesEngine
from PC_ENGINE.core.order_manager import OrderManager
from PC_ENGINE.core.paper_broker import PaperBroker
from PC_ENGINE.core.preflight import PreflightChecker
from PC_ENGINE.core.recovery import RecoveryManager
from PC_ENGINE.core.risk import RiskEngine
from PC_ENGINE.core.real_readiness_service import RealReadinessService
from PC_ENGINE.core.real_mode_guard import RealModeGuard
from PC_ENGINE.core.execution_gate import ExecutionGate, ExecutionState
from PC_ENGINE.core.strategy import TrendEmaAtrStrategy
from PC_ENGINE.exchanges.ccxt_client import CcxtExchangeClient
from PC_ENGINE.learning.champion_challenger import ChampionChallenger
from PC_ENGINE.services.paper_market_collector import PaperMarketCollector
from PC_ENGINE.services.watchdog import Watchdog
from PC_ENGINE.human_bridge.bridge import HumanInteractionBridge
from PC_ENGINE.human_bridge.watchdog import HumanBridgeWatchdog
from PC_ENGINE.radar.market_state import MarketStateStore
from PC_ENGINE.storage.ledger import Ledger
from PC_ENGINE.execution.browser_execution_ledger import BrowserExecutionLedger
from PC_ENGINE.research.autonomous import AutonomousResearchWorker
from PC_ENGINE.research.worker import ResearchWorker
from PC_ENGINE.core.shared_intelligence import SharedIntelligenceStore
from PC_ENGINE.core.shared_intelligence_sync import SharedIntelligenceSync
from PC_ENGINE.core.shared_intelligence_sync_worker import SharedIntelligenceSyncWorker
from PC_ENGINE.core.vercel_shared_intelligence import VercelSharedIntelligenceProvider


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
    human_bridge: Dict[str, object] = field(default_factory=dict)
    operational: Dict[str, object] = field(default_factory=dict)
    preflight: Dict[str, object] = field(default_factory=dict)
    account_reconciliation: Dict[str, object] = field(default_factory=dict)
    financial_reconciliation: Dict[str, object] = field(default_factory=dict)
    financial_account: Dict[str, object] = field(default_factory=dict)
    champion_challenger: Dict[str, object] = field(default_factory=dict)
    paper_collector: Dict[str, object] = field(default_factory=dict)
    research: Dict[str, object] = field(default_factory=dict)
    shared_intelligence: Dict[str, object] = field(default_factory=dict)
    pending_orders: Dict[str, dict] = field(default_factory=dict)
    execution_intents: Dict[str, dict] = field(default_factory=dict)
    logs: List[str] = field(default_factory=list)


class SovereignEngine:
    def __init__(self, config: dict):
        self.config = config
        self.owner_context = OwnerContext.from_config(config, DATA_DIR)
        self.owner_id = self.owner_context.owner_id
        config.setdefault("owner", {})["id"] = self.owner_id
        configured_mode = str(config.get("mode", "PAPER")).upper()
        # A process restart can never inherit a protected REAL mode from
        # configuration alone. REAL must be entered through the guarded API
        # transition after readiness and explicit operator authorization.
        self.mode = self._startup_mode(configured_mode)
        self.paper = self.mode != "REAL"
        self.real_operational = False
        self.real_fail_safe_reason = ""
        self.real_mode_guard = RealModeGuard(config.get("real_mode_guard", {}))
        self.execution_gate = ExecutionGate()
        self.real_readiness_service = RealReadinessService(config)
        self._autonomous_real_promotion_attempted = False
        self.state = RuntimeState(mode=self.mode)
        self.state.operational["owner_id"] = self.owner_id
        self.ledger = Ledger(
            path=self.owner_context.private_path("logs/trades.jsonl"),
            events_path=self.owner_context.private_path("logs/events.jsonl"),
        )
        self.rules = ExchangeRulesEngine()
        paper_cfg = dict(config.get("paper", {}))
        paper_cfg["autonomous_intents_path"] = str(self.owner_context.private_path("paper/autonomous_intents.jsonl"))
        paper_cfg["fills_path"] = str(self.owner_context.private_path("paper/fills.jsonl"))
        paper_cfg["runs_path"] = str(self.owner_context.private_path("paper/runs.jsonl"))
        paper_cfg["reconciliation_path"] = str(self.owner_context.private_path("paper/autonomous_reconciliation.json"))
        config["paper"] = paper_cfg
        self.paper_broker = PaperBroker(
            fee_pct=float(paper_cfg.get("fee_pct", 0.001)),
            slippage_pct=float(paper_cfg.get("slippage_pct", 0.0005)),
            reject_probability=float(paper_cfg.get("reject_probability", 0.0)),
        )
        self.order_manager = OrderManager(self.rules, self.paper_broker)
        self.recovery = RecoveryManager(state_path=self.owner_context.private_path("runtime_state.json"))
        self.browser_execution_ledger = BrowserExecutionLedger(self.owner_context.private_path("execution/browser.jsonl"))
        self.watchdog = Watchdog()
        self.ai_council = DisabledAICouncil()
        self.champion = ChampionChallenger()
        self.risk = RiskEngine(config["risk"])
        strategy_config = dict(config["strategy"])
        # Market-data quality is a global contract shared by every OHLCV consumer.
        # Propagate it into the strategy so the primary engine cycle cannot bypass
        # the same freshness/continuity gate used by the PAPER collector.
        strategy_config["market_data_quality"] = dict(config.get("market_data_quality", {}))
        self.strategy = TrendEmaAtrStrategy(strategy_config)
        self.allocator = CapitalAllocator(config["engine"], config.get("symbol_limits", {}))
        self.opportunity = PaperOpportunityEngine(config.get("opportunity", {}))
        self.market_states = MarketStateStore(config.get("opportunity", {}).get("data_dir", "PC_ENGINE/data/radar"))
        self.exchanges = self._build_exchanges()
        self.paper_collector: PaperMarketCollector | None = None
        self._build_paper_collector()
        self.thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.lock = threading.RLock()
        human_cfg = dict(config.get("human_bridge", {}))
        human_cfg["data_dir"] = str(self.owner_context.private_path("human_bridge"))
        research_cfg = dict(config.get("research", {}))
        self.human_bridge = HumanInteractionBridge(
            human_cfg.get("data_dir"),
            default_ttl_seconds=int(human_cfg.get("human_interaction_ttl_seconds", human_cfg.get("response_timeout_seconds", 900))),
        )
        self.human_bridge_watchdog = HumanBridgeWatchdog(self.human_bridge, human_cfg)
        self._human_bridge_operational_last_state = None
        self.cycle_count = 0
        self.preflight_done = False
        research_dir = str(self.owner_context.private_path("research"))
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
        self.shared_intelligence_store: SharedIntelligenceStore | None = None
        self.shared_intelligence_sync: SharedIntelligenceSync | None = None
        self.shared_intelligence_worker: SharedIntelligenceSyncWorker | None = None
        self._build_shared_intelligence_sync()
        self._load_recovery_state()

    def _build_shared_intelligence_sync(self) -> None:
        cfg = dict(self.config.get("shared_intelligence", {}))
        enabled = bool(cfg.get("enabled", True))
        sync_enabled = bool(cfg.get("sync_enabled", False))
        self.state.shared_intelligence = {
            "enabled": enabled,
            "sync_enabled": sync_enabled,
            "provider": str(cfg.get("sync_provider", "vercel")),
            "state": "DISABLED" if not enabled or not sync_enabled else "NOT_CONFIGURED",
            "bootstrap": False,
        }
        if not enabled or not sync_enabled:
            return

        store_path = str(cfg.get("store_path", "PC_ENGINE/data/shared_intelligence/artifacts.jsonl"))
        state_path = str(cfg.get("state_path", "PC_ENGINE/data/shared_intelligence/sync_state.json"))
        self.shared_intelligence_store = SharedIntelligenceStore(store_path)
        self.shared_intelligence_sync = SharedIntelligenceSync(self.shared_intelligence_store, state_path, pull_limit=int(cfg.get("pull_limit", 500)))
        provider_name = str(cfg.get("sync_provider", "vercel")).lower()
        if provider_name != "vercel":
            self.state.shared_intelligence.update({"state": "UNSUPPORTED_PROVIDER"})
            return
        base_url = env_value(str(cfg.get("base_url_env", "VST_SHARED_INTELLIGENCE_URL")), "")
        token = env_value(str(cfg.get("token_env", "VST_SHARED_INTELLIGENCE_TOKEN")), "")
        if not base_url or not token:
            self.state.shared_intelligence.update({
                "state": "WAITING_FOR_PROVIDER_CONFIG",
                "missing": [name for name, value in (("base_url", base_url), ("token", token)) if not value],
            })
            return
        provider = VercelSharedIntelligenceProvider(base_url, token, timeout_seconds=float(cfg.get("timeout_seconds", 5.0)))
        self.shared_intelligence_worker = SharedIntelligenceSyncWorker(
            self.shared_intelligence_store, self.shared_intelligence_sync, provider,
            pull_interval_seconds=float(cfg.get("pull_interval_seconds", 86400.0)),
            push_interval_seconds=float(cfg.get("push_interval_seconds", 86400.0)),
        )
        self.state.shared_intelligence.update({
            "state": "READY",
            "pull_interval_seconds": float(cfg.get("pull_interval_seconds", 86400.0)),
            "push_interval_seconds": float(cfg.get("push_interval_seconds", 86400.0)),
        })

    def _sync_shared_intelligence_before_start(self) -> None:
        """Start best-effort sync asynchronously; never wait on cloud during engine startup."""
        worker = self.shared_intelligence_worker
        if worker is None:
            return
        try:
            worker.start()
            self.state.shared_intelligence.update({
                "state": "BACKGROUND_SYNC_SCHEDULED",
                "bootstrap": bool(worker.bootstrap_done),
                "pull_interval_seconds": worker.pull_interval,
                "push_interval_seconds": worker.push_interval,
            })
        except Exception as exc:
            # A sync worker failure is operational telemetry only; local trading remains independent.
            self.state.shared_intelligence.update({"state": "DEGRADED", "error": type(exc).__name__})

    def _stop_shared_intelligence(self) -> None:
        worker = self.shared_intelligence_worker
        if worker is None:
            return
        worker.stop()
        self.state.shared_intelligence.update({"state": "STOPPED", "bootstrap": bool(worker.bootstrap_done), "last_result": dict(worker.last_result)})

    @staticmethod
    def _startup_mode(configured_mode: str) -> str:
        """Normalize startup mode so a restart can never inherit REAL."""
        mode = str(configured_mode or "PAPER").upper()
        return "PAPER" if mode == "REAL" else mode

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
        collector_cfg["market_data_quality"] = dict(self.config.get("market_data_quality", {}))
        collector_cfg["evidence"] = dict(self.config.get("evidence", {}))
        self.paper_collector = PaperMarketCollector(
            settings=collector_cfg,
            symbols=self.config.get("symbols", []),
            ohlcv_fetcher=self._fetch_ohlcv_for_collector,
            strategy=getattr(self, "strategy", None),
            on_error=self.log,
        )

    def _fetch_ohlcv_for_collector(self, symbol: str, timeframe: str, limit: int) -> list[list[float]]:
        exchange = self._main_exchange()
        if exchange is None:
            return []
        return exchange.fetch_ohlcv(symbol, timeframe, limit)

    def _load_recovery_state(self) -> None:
        try:
            journal = self.recovery.load_reconciliation_journal()
            if journal is not None:
                transaction_id = str(journal.get("transaction_id") or "")
                if not transaction_id:
                    raise RuntimeError("reconciliation journal missing transaction_id")
                self.recovery.commit_reconciliation(transaction_id)
                for ledger_entry in journal.get("ledger_records", []):
                    self.ledger.trade_idempotent(dict(ledger_entry.get("record") or {}), str(ledger_entry.get("reconciliation_key") or ""))
                self.recovery.clear_reconciliation()
                committed = self.recovery.load_state()
                self.state.pending_orders = dict(committed.get("pending_orders", {}))
                self.state.financial_account = dict(committed.get("financial_account", {}))
                restored_positions = {}
                for restored_symbol, restored_data in dict(committed.get("positions", {})).items():
                    restored_positions[restored_symbol] = Position(**restored_data)
                self.state.open_positions = restored_positions
                risk_obj = getattr(self, "risk", None)
                if risk_obj is not None and committed.get("risk_state"):
                    risk_obj.restore_state(committed["risk_state"])
                self.log("RECOVERY_RECONCILIATION_TRANSACTION_COMMITTED", {"transaction_id": transaction_id})
        except Exception as exc:
            self._enter_safe_state("reconciliation_journal_corrupt")
            self.state.operational["reconciliation_journal_error"] = f"{type(exc).__name__}: {exc}"
            self.log("RECOVERY_RECONCILIATION_JOURNAL_BLOCK_START", {"error": str(exc)})
            return
        raw_state = self.recovery.load_state()
        recovery_error = str(raw_state.get("recovery_error", "")).strip()
        if recovery_error:
            self._enter_safe_state("recovery_state_corrupt")
            self.state.operational["recovery_state_corrupt"] = True
            self.state.operational["recovery_error"] = recovery_error
            self.log("RECOVERY_STATE_CORRUPT", {"error": recovery_error})
            return
        raw_positions = raw_state.get("positions", {})
        pending = raw_state.get("pending_orders", {})
        intents = raw_state.get("execution_intents", {})
        financial_account = raw_state.get("financial_account", {})
        if isinstance(financial_account, dict):
            self.state.financial_account.update(financial_account)
        risk_state = raw_state.get("risk_state", {})
        if risk_state:
            try:
                self.risk.restore_state(risk_state)
            except Exception as exc:
                self._enter_safe_state("recovery_state_corrupt")
                self.state.operational["recovery_state_corrupt"] = True
                self.state.operational["recovery_error"] = f"risk_state: {type(exc).__name__}: {exc}"
                self.log("RECOVERY_RISK_STATE_CORRUPT", {"error": str(exc)})
                return
        self.state.pending_orders.update(pending)
        self.state.execution_intents.update(intents)
        self._recover_browser_submissions()
        self.order_manager.restore_order_guards(raw_state.get("order_guards", {}))
        if pending:
            self._enter_safe_state("critical_runtime_condition")
            self.log("RECOVERY_PENDING_ORDERS", {"order_ids": list(pending)})
        if intents:
            self._enter_safe_state("critical_runtime_condition")
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

    def _recover_browser_submissions(self) -> None:
        """Promote durable browser submissions into normal pending-order recovery."""
        try:
            submissions = self.browser_execution_ledger.pending_submissions()
        except Exception:
            return
        for record in submissions:
            order_id = str(record.external_id or "").strip()
            recovery_id = order_id or ("browser-client:" + record.idempotency_key)
            if recovery_id in self.state.pending_orders:
                continue
            side = str(record.action or "").lower()
            if side not in {"buy", "sell"}:
                self._enter_safe_state("critical_runtime_condition")
                self.log("BROWSER_RECOVERY_INVALID_SIDE", {"idempotency_key": record.idempotency_key, "side": side})
                continue
            self.state.pending_orders[recovery_id] = {
                "symbol": record.symbol,
                "side": side,
                "requested_qty": float(record.quantity),
                "known_filled_qty": 0.0,
                "known_fill_price": 0.0,
                "known_quote_notional": 0.0,
                "known_fee": 0.0,
                "client_order_id": record.idempotency_key,
                "created_ts": record.recorded_at_ms / 1000.0,
                "browser_execution": True,
                "venue_id": record.venue_id,
                "account_id": record.account_id,
                "stop_pct": record.stop_pct,
                "take_profit_pct": record.take_profit_pct,
            }
            self._enter_safe_state("critical_runtime_condition")
            self.log("BROWSER_PENDING_ORDER_RECOVERED", {"order_id": order_id, "recovery_id": recovery_id, "symbol": record.symbol, "side": side, "idempotency_key": record.idempotency_key})

    def _persist_recovery(self) -> None:
        self.recovery.save_positions(
            self.state.open_positions,
            self.state.pending_orders,
            self.order_manager.export_order_guards(),
            self.state.execution_intents,
            self.state.financial_account,
            self.risk.snapshot_state(),
        )

    def _record_financial_fill(self, side: str, symbol: str, qty: float, quote_notional: float, fee: float) -> None:
        if getattr(self, "paper", False) or qty <= 0 or quote_notional < 0 or fee < 0:
            return
        base_asset = str(symbol).split("/", 1)[0]
        financial = self.state.financial_account
        base_flow = financial.setdefault("base_flow", {})
        signed_qty = float(qty) if side == "buy" else -float(qty) if side == "sell" else 0.0
        if not signed_qty:
            return
        base_flow[base_asset] = float(base_flow.get(base_asset, 0.0) or 0.0) + signed_qty
        quote_flow = float(financial.get("quote_flow", 0.0) or 0.0)
        financial["quote_flow"] = quote_flow - float(quote_notional) - float(fee) if side == "buy" else quote_flow + float(quote_notional) - float(fee)

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
            quote_flow = float(financial.get("quote_flow", 0.0) or 0.0)
            base_flow = financial.setdefault("base_flow", {})

            expected_by_asset: dict[str, float] = {}
            symbols_by_asset: dict[str, list[str]] = {}
            for symbol, position in self.state.open_positions.items():
                base_asset = str(symbol).split("/", 1)[0]
                expected_by_asset[base_asset] = expected_by_asset.get(base_asset, 0.0) + float(position.qty)
                symbols_by_asset.setdefault(base_asset, []).append(symbol)

            position_baseline = financial.get("position_baseline_qty")
            if not isinstance(position_baseline, dict):
                position_baseline = {asset: float(qty) for asset, qty in expected_by_asset.items()}
                financial["position_baseline_qty"] = dict(position_baseline)
                financial["initialized_at"] = time.time()
            baseline = financial.get("baseline_total")
            if baseline is None:
                baseline = {str(k): float(v or 0.0) for k, v in total.items() if str(k) == quote}
                financial["baseline_total"] = baseline
                financial["quote_flow"] = quote_flow
                financial["initialized_at"] = time.time()
            baseline_quote = float(baseline.get(quote, 0.0) or 0.0)
            expected_quote = baseline_quote + quote_flow
            exchange_quote = float(total.get(quote, 0.0) or 0.0)
            quote_tol = max(dust_tolerance, abs(expected_quote) * financial_tolerance)
            quote_mismatch = abs(exchange_quote - expected_quote) > quote_tol

            base_flow_mismatches = []
            for asset in set(position_baseline) | set(expected_by_asset) | set(base_flow):
                expected_position = float(position_baseline.get(asset, 0.0) or 0.0) + float(base_flow.get(asset, 0.0) or 0.0)
                current_position = float(expected_by_asset.get(asset, 0.0) or 0.0)
                tolerance = max(dust_tolerance, abs(expected_position) * financial_tolerance)
                if abs(current_position - expected_position) > tolerance:
                    base_flow_mismatches.append({
                        "asset": asset,
                        "expected": expected_position,
                        "local": current_position,
                        "tolerance": tolerance,
                    })

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
                if asset_name not in expected_by_asset and asset_name not in base_flow:
                    unexpected_assets.append({
                        "asset": asset_name,
                        "total": qty,
                        "reason": "exchange_asset_without_local_position",
                    })

            result = {
                "ok": not mismatches and not base_flow_mismatches and not unexpected_assets and not open_orders and not quote_mismatch,
                "status": "MATCH" if not mismatches and not base_flow_mismatches and not unexpected_assets and not open_orders and not quote_mismatch else "BLOCKED",
                "tracked_positions": len(self.state.open_positions),
                "expected_assets": expected_by_asset,
                "open_orders": len(open_orders),
                "mismatches": mismatches,
                "unexpected_assets": unexpected_assets,
                "open_order_ids": [str(o.get("id", "")) for o in open_orders if o.get("id")],
                "dust_tolerance": dust_tolerance,
                "relative_tolerance": relative_tolerance,
                "financial_account": dict(financial),
                "base_flow_mismatches": base_flow_mismatches,
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
            self._enter_safe_state("critical_runtime_condition")
            self.log("ACCOUNT_RECONCILIATION_BLOCKED", result)
        else:
            self.log("ACCOUNT_RECONCILIATION_MATCH", result)
        return result

    def log(self, message: str, data: dict | None = None) -> None:
        row = message if data is None else f"{message}: {data}"
        lock = getattr(self, "lock", None)
        if lock is None:
            lock = threading.RLock()
            self.lock = lock
        with lock:
            self.state.logs.append(row)
            self.state.logs = self.state.logs[-100:]
        ledger = getattr(self, "ledger", None)
        if ledger is not None and hasattr(ledger, "event"):
            ledger.event(message, data or {})

    def _enter_real_fail_safe(self, reason: str, data: dict | None = None) -> None:
        """Leave REAL immediately on a critical runtime condition."""
        gate = getattr(self, "execution_gate", None)
        if gate is not None:
            gate.fail_safe(str(reason))
        if getattr(self, "mode", "PAPER") != "REAL":
            self.state.status = "SAFE_MODE"
            self.real_operational = False
            return
        self.real_fail_safe_reason = str(reason)
        self.real_operational = False
        self.mode = "PAPER"
        self.paper = True
        self.state.mode = "PAPER"
        self.exchanges = self._build_exchanges()
        guard = getattr(self, "real_mode_guard", None)
        if guard is not None:
            guard.disarm(f"REAL fail-safe: {reason}")
        self._build_paper_collector()
        if self.paper_collector is not None:
            try:
                self.paper_collector.start()
            except Exception:
                pass
        self.state.status = "SAFE_MODE"
        payload = {"reason": reason}
        if data:
            payload.update(data)
        self.log("REAL_FAIL_SAFE", payload)

    def _enter_safe_state(self, reason: str, data: dict | None = None) -> None:
        if getattr(self, "mode", "PAPER") == "REAL":
            self._enter_real_fail_safe(reason, data)
        else:
            self.state.status = "SAFE_MODE"

    def start(self) -> None:
        if self.thread and self.thread.is_alive():
            self.pause(False)
            return
        preflight = self.run_preflight()
        if self.config.get("engine", {}).get("preflight_required", True) and not preflight["ok"]:
            self._enter_safe_state("preflight_failed", preflight)
            self.log("PREFLIGHT_BLOCKED_START", preflight)
            return
        if self.state.execution_intents:
            # Recovery is a mandatory dependency for unresolved execution intents.
            # A partially constructed engine/test fixture must fail closed explicitly,
            # rather than reaching _persist_recovery() and failing with AttributeError.
            recovery = getattr(self, "recovery", None)
            if not isinstance(recovery, RecoveryManager):
                self._enter_safe_state("recovery_dependency_missing", {
                    "dependency": "RecoveryManager",
                    "intent_ids": list(self.state.execution_intents),
                })
                self.log("RECOVERY_DEPENDENCY_MISSING_BLOCK_START", {
                    "dependency": "RecoveryManager",
                    "intent_ids": list(self.state.execution_intents),
                })
                self.log("RECOVERY_UNRESOLVED_EXECUTION_INTENTS_BLOCK_START", {
                    "intent_ids": list(self.state.execution_intents),
                })
                return
            self._recover_unresolved_execution_intents()
            if self.state.execution_intents:
                self._enter_safe_state("unresolved_execution_intents", {"intent_ids": list(self.state.execution_intents)})
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
                self._enter_safe_state("account_reconciliation_failed", reconciliation)
                self.log("REAL_START_BLOCKED_ACCOUNT_RECONCILIATION", reconciliation)
                return
        self.stop_event.clear()
        self.research_stop_event.clear()
        self._sync_shared_intelligence_before_start()
        self.state.status = "RUNNING"
        self.real_operational = self.mode == "REAL"
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
        self._stop_shared_intelligence()
        if self.paper_collector is not None:
            self.paper_collector.stop()
        if self.research_thread is not None and self.research_thread.is_alive():
            self.research_thread.join(timeout=1.0)
        with self.lock:
            self.state.status = "OFF"
            self.state.paper_collector = self.paper_collector.snapshot() if self.paper_collector else {"running": False}
        self._persist_recovery()
        self.log("ENGINE_STOPPED")

    def set_mode(self, mode: str, *, real_authorized: bool = False, autonomous: bool = False) -> None:
        mode = mode.upper()
        if mode not in {"PAPER", "REAL"}:
            raise ValueError("mode must be PAPER or REAL")
        if mode == "REAL" and not real_authorized:
            raise RuntimeError("REAL mode requires guarded operator authorization")
        if mode == "REAL" and not bool(self.config.get("autonomous_execution", {}).get("allow_real", False)):
            raise RuntimeError("REAL mode disabled by configuration")
        if mode == "REAL":
            # The autonomous readiness path also consumes a one-time authorization
            # before calling set_mode. The flag is not a capability and must never
            # bypass this freshness check for direct callers.
            guard = getattr(self, "real_mode_guard", None)
            guard_state = getattr(guard, "state", None)
            if guard_state is None or str(getattr(guard_state, "last_reason", "")) != "authorization consumed":
                raise RuntimeError("REAL mode requires a freshly consumed human authorization")
        if mode == "REAL" and self.state.status == "RUNNING" and not autonomous:
            raise RuntimeError("Stop the engine before switching to REAL")
        if mode == "REAL":
            guard = getattr(self, "real_mode_guard", None)
            if guard is None or not bool(getattr(getattr(guard, "state", None), "human_authorized", False)):
                raise RuntimeError("REAL mode requires the RealModeGuard's initial human authorization")
            gate = getattr(self, "execution_gate", None)
            if gate is None:
                raise RuntimeError("REAL mode execution gate is not initialized")
            if not gate.human_authorized or (gate.state == ExecutionState.SAFEGUARD_PAPER and not autonomous):
                gate.human_authorize()
            if gate.state in {ExecutionState.PAPER, ExecutionState.REAL_AUTHORIZED}:
                activation = gate.activate_real()
                if not activation.allowed:
                    raise RuntimeError(f"REAL execution gate blocked: {activation.reason}")
            elif gate.state not in {ExecutionState.REAL_ACTIVE, ExecutionState.SAFEGUARD_PAPER, ExecutionState.REAL_RECOVERY_ELIGIBLE}:
                raise RuntimeError(f"REAL execution gate blocked: {gate.state.value}")
        elif getattr(self, "execution_gate", None) is not None:
            self.execution_gate.reset_to_paper()
        if mode == "REAL" and self.paper_collector is not None:
            self.paper_collector.stop()
        self.mode = mode
        self.paper = mode != "REAL"
        self.real_operational = False
        if mode == "REAL":
            self.real_fail_safe_reason = ""
        self.state.mode = mode
        self.exchanges = self._build_exchanges()
        if self.paper:
            self._build_paper_collector()
        else:
            self.paper_collector = None
        self.log("MODE_CHANGED", {"mode": mode})

    def fail_safe_real(self, reason: str, data: dict | None = None) -> None:
        self._enter_real_fail_safe(reason, data)

    def snapshot(self) -> dict:
        with self.lock:
            data = asdict(self.state)
            data["owner"] = self.owner_context.snapshot()
            data["open_positions"] = {k: asdict(v) for k, v in self.state.open_positions.items()}
            data["paper_collector"] = self.paper_collector.snapshot() if self.paper_collector else {"running": False}
            data["real_operational"] = self.real_operational
            data["real_fail_safe_reason"] = self.real_fail_safe_reason
            gate = getattr(self, "execution_gate", None)
            data["execution_gate"] = {
                "state": gate.state.value,
                "human_authorized": gate.human_authorized,
            } if gate is not None else {"state": "MISSING", "human_authorized": False}
            if self.shared_intelligence_worker is not None:
                data["shared_intelligence"] = {**self.state.shared_intelligence, "bootstrap": bool(self.shared_intelligence_worker.bootstrap_done), "last_result": dict(self.shared_intelligence_worker.last_result)}
            return data

    def _main_exchange(self) -> CcxtExchangeClient | None:
        exchanges = getattr(self, "exchanges", {}) or {}
        return next(iter(exchanges.values()), None)

    def _loop(self) -> None:
        while not self.stop_event.is_set():
            if self.state.status == "PAUSED":
                time.sleep(1)
                continue
            try:
                self.cycle()
            except Exception as exc:
                self._enter_safe_state("engine_exception", {"error": str(exc)})
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
                self._enter_safe_state("watchdog_internet_failure", asdict(status))
                self.log("WATCHDOG_BLOCK", asdict(status))
                return False
            symbol = self.config["symbols"][0]
            ex_status = self.watchdog.check_exchange(exchange, symbol)
            self.state.watchdog = asdict(ex_status)
            if not ex_status.ok:
                self._enter_safe_state("watchdog_exchange_failure", asdict(ex_status))
                self.log("WATCHDOG_EXCHANGE_BLOCK", asdict(ex_status))
                return False
        return True

    def refresh_human_bridge_operational_state(self, now: float | None = None) -> dict:
        """Project Human Bridge liveness into engine operational telemetry.

        A stale Android/PC bridge is control-plane degradation only. It never
        changes engine.status, never enters SAFE_MODE and never blocks the
        trading path because the browser bridge is not the trading executor.
        Pending human interactions are reported as blocked until the bridge
        recovers or their normal TTL expires.
        """
        if not bool(self.config.get("human_bridge", {}).get("enabled", True)):
            report = {
                "state": "DISABLED",
                "trading_impact": "NONE",
                "action": "CONTINUE_TRADING",
                "human_interaction_required": 0,
                "safe_state": False,
            }
            self.state.human_bridge = report
            self.state.operational = {"state": "HEALTHY", "trading_impact": "NONE", "action": "CONTINUE_TRADING"}
            return report

        report = self.human_bridge_watchdog.check(now)
        mobile = report.get("mobile", {})
        pc = report.get("pc", {})
        mobile_seen = float(mobile.get("last_seen") or 0.0) > 0.0
        pc_seen = float(pc.get("last_seen") or 0.0) > 0.0
        mobile_stale = bool(mobile.get("stale", True))
        pc_stale = bool(pc.get("stale", True))
        pending = sum(
            1 for item in self.human_bridge.snapshot().get("requests", [])
            if item.get("status") in {"PENDING", "RESPONDED"}
        )

        if not mobile_seen and not pc_seen:
            state = "NOT_CONNECTED"
        elif not mobile_stale and not pc_stale:
            state = "HEALTHY"
        elif mobile_stale and pc_stale:
            state = "BRIDGE_UNAVAILABLE"
        else:
            state = "DEGRADED"

        action = "CONTINUE_TRADING"
        if state in {"DEGRADED", "BRIDGE_UNAVAILABLE"} and pending:
            action = "HUMAN_INTERACTION_BLOCKED"

        payload = {
            **report,
            "state": state,
            "trading_impact": "NONE",
            "action": action,
            "human_interaction_required": pending,
        }
        self.state.human_bridge = payload
        self.state.operational = {
            "state": state,
            "trading_impact": "NONE",
            "action": action,
            "human_interaction_required": pending,
        }
        if state != self._human_bridge_operational_last_state:
            self._human_bridge_operational_last_state = state
            self.log("HUMAN_BRIDGE_OPERATIONAL_STATE", {
                "state": state,
                "action": action,
                "human_interaction_required": pending,
            })
        return payload

    def _recover_unresolved_execution_intents(self) -> None:
        """Recover unresolved intents only from the exact recorded venue and identity.

        Recovery never assumes a fill. Missing venue identity or incomplete/mismatched
        order identity leaves the intent unresolved and keeps the engine fail-closed.
        """
        if not self.state.execution_intents or self.paper:
            return
        configured_exchanges = getattr(self, "exchanges", {}) or {}
        open_orders_by_exchange: dict[int, list] = {}

        for intent_id, intent in list(self.state.execution_intents.items()):
            symbol = str(intent.get("symbol", "")).strip()
            side = str(intent.get("side", "")).lower()
            try:
                requested = float(intent.get("requested_qty") or 0.0)
            except (TypeError, ValueError, OverflowError):
                requested = float("nan")
            if not symbol or side not in {"buy", "sell"} or not math.isfinite(requested) or requested <= 0:
                self._enter_safe_state("critical_runtime_condition")
                self.log("EXECUTION_INTENT_INVALID", {
                    "intent_id": intent_id, "symbol": symbol, "side": side,
                    "requested_qty": intent.get("requested_qty"),
                })
                continue

            recorded_exchange = str(intent.get("exchange") or "").strip()
            exchange = next((
                candidate for key, candidate in configured_exchanges.items()
                if str(key) == recorded_exchange
                or str(getattr(candidate, "name", "")) == recorded_exchange
            ), None)
            if exchange is None:
                main_exchange = self._main_exchange()
                if main_exchange is not None and str(getattr(main_exchange, "name", "")) == recorded_exchange:
                    exchange = main_exchange
            if exchange is None:
                self._enter_safe_state("critical_runtime_condition")
                self.log("EXECUTION_INTENT_VENUE_UNAVAILABLE", {
                    "intent_id": intent_id, "recorded_exchange": recorded_exchange,
                    "symbol": symbol,
                })
                continue

            cache_key = id(exchange)
            if cache_key not in open_orders_by_exchange:
                try:
                    open_orders_by_exchange[cache_key] = exchange.fetch_open_orders()
                except Exception as exc:
                    self._enter_safe_state("critical_runtime_condition")
                    self.log("EXECUTION_INTENT_RECOVERY_BLOCKED", {
                        "intent_id": intent_id, "exchange": recorded_exchange, "error": str(exc),
                    })
                    continue
            open_orders = open_orders_by_exchange[cache_key]
            client_order_id = str(intent.get("client_order_id") or "").strip()
            matches = []

            def identity_matches(order: dict, *, require_client_id: bool) -> bool:
                order_id = order.get("id")
                order_symbol = str(order.get("symbol") or "").strip()
                order_side = str(order.get("side") or "").lower()
                order_client_id = str(order.get("clientOrderId") or order.get("client_order_id") or "").strip()
                amount_raw = order.get("amount") if order.get("amount") is not None else order.get("origQty")
                if amount_raw is None:
                    amount_raw = order.get("quantity")
                try:
                    amount = float(amount_raw)
                except (TypeError, ValueError, OverflowError):
                    return False
                return bool(
                    order_id
                    and order_symbol == symbol
                    and order_side == side
                    and math.isfinite(amount)
                    and amount > 0
                    and abs(amount - requested) <= max(1e-12, requested * 1e-9)
                    and (not require_client_id or (client_order_id and order_client_id == client_order_id))
                )

            if client_order_id:
                matches = [order for order in open_orders if identity_matches(order, require_client_id=True)]
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
                    if isinstance(historical, dict) and historical.get("id"):
                        if identity_matches(historical, require_client_id=True):
                            order = historical
                            matches = [order]
                        else:
                            self._enter_safe_state("critical_runtime_condition")
                            self.log("EXECUTION_INTENT_HISTORICAL_IDENTITY_MISMATCH", {
                                "intent_id": intent_id,
                                "returned_order_id": str(historical.get("id")),
                                "expected_client_order_id": client_order_id,
                                "returned_client_order_id": str(historical.get("clientOrderId") or historical.get("client_order_id") or ""),
                                "expected_symbol": symbol,
                                "returned_symbol": str(historical.get("symbol") or ""),
                                "expected_side": side,
                                "returned_side": str(historical.get("side") or ""),
                            })
                            continue
                    else:
                        self._enter_safe_state("critical_runtime_condition")
                        self.log("EXECUTION_INTENT_ORDER_UNRESOLVED", {
                            "intent_id": intent_id, "client_order_id": client_order_id,
                            "exchange": recorded_exchange, "match_count": len(matches),
                        })
                        continue
            else:
                matches = [order for order in open_orders if identity_matches(order, require_client_id=False)]
                if len(matches) != 1:
                    self._enter_safe_state("critical_runtime_condition")
                    self.log("EXECUTION_INTENT_ORDER_UNRESOLVED", {
                        "intent_id": intent_id, "exchange": recorded_exchange,
                        "match_count": len(matches), "reason": "no_unique_identity_match",
                    })
                    continue

            order = matches[0]
            order_id = str(order["id"])
            self.state.pending_orders[order_id] = {
                "exchange": exchange.name,
                "venue_id": recorded_exchange,
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
            self.log("EXECUTION_INTENT_RECOVERED_ORDER", {
                "intent_id": intent_id, "order_id": order_id, "exchange": recorded_exchange,
                "symbol": symbol, "side": side,
            })
        self._persist_recovery()

    def _extract_cumulative_quote_fee(self, raw: dict, symbol: str) -> float:
        """Return a finite, non-negative fee only when quote denomination is proven.

        Missing fee data is treated as zero for adapters that omit fees. A reported
        non-zero fee without currency evidence is ambiguous and must not be booked
        as quote currency.
        """
        fee_entries = raw.get("fees")
        if isinstance(fee_entries, list) and fee_entries:
            entries = fee_entries
        else:
            single = raw.get("fee")
            entries = [single] if isinstance(single, dict) else []
        quote = str(symbol).split("/", 1)[1].strip().upper() if "/" in symbol else ""
        if not entries:
            single = raw.get("fee")
            if single is None:
                return 0.0
            if isinstance(single, (int, float, str)):
                try:
                    amount = float(single)
                except (TypeError, ValueError, OverflowError) as exc:
                    raise ValueError("invalid fee amount") from exc
                if not math.isfinite(amount) or amount < 0:
                    raise ValueError("fee amount must be finite and non-negative")
                if amount > 0:
                    raise ValueError("fee currency is unknown; refusing quote-denominated accounting")
                return 0.0
            raise ValueError("unsupported fee representation")

        total = 0.0
        saw_amount = False
        for entry in entries:
            if not isinstance(entry, dict):
                raise ValueError("invalid fee entry")
            cost = entry.get("cost")
            if cost is None:
                cost = entry.get("amount")
            if cost is None:
                continue
            try:
                amount = float(cost)
            except (TypeError, ValueError, OverflowError) as exc:
                raise ValueError("invalid fee amount") from exc
            if not math.isfinite(amount) or amount < 0:
                raise ValueError("fee amount must be finite and non-negative")
            saw_amount = True
            currency = str(entry.get("currency") or "").strip().upper()
            if amount > 0 and (not currency or not quote or currency != quote):
                raise ValueError(
                    f"fee currency is missing or not quote-denominated for {symbol}: {currency or 'UNKNOWN'}"
                )
            total += amount
        if not saw_amount:
            return 0.0
        if not math.isfinite(total):
            raise ValueError("cumulative fee is not finite")
        return total

    def _validate_order_financial_invariant(self, raw: dict, symbol: str, filled_qty: float, average_price: float) -> dict:
        cfg = getattr(self, "config", {}).get("reconciliation", {})
        tolerance_pct = max(0.0, float(cfg.get("financial_relative_tolerance", 0.002)))
        cost = raw.get("cost")
        if cost is not None:
            cost = float(cost)
            if not math.isfinite(cost):
                return {"ok": False, "reason": "nonfinite_order_cost", "cost": cost}
            expected = float(filled_qty) * float(average_price)
            tolerance = max(1e-12, abs(expected) * tolerance_pct)
            if cost < 0:
                return {"ok": False, "reason": "negative_order_cost", "cost": cost}
            if abs(cost - expected) > tolerance:
                return {
                    "ok": False,
                    "reason": "order_cost_price_quantity_mismatch",
                    "reported_cost": cost,
                    "expected_cost": expected,
                    "tolerance": tolerance,
                }
        fee = raw.get("fee")
        fee_costs = []
        if isinstance(fee, dict) and fee.get("cost") is not None:
            fee_cost = float(fee["cost"])
            if not math.isfinite(fee_cost):
                return {"ok": False, "reason": "nonfinite_fee", "fee": fee_cost}
            if fee_cost < 0:
                return {"ok": False, "reason": "negative_fee", "fee": fee_cost}
            fee_costs.append(fee_cost)
        fees = raw.get("fees")
        if isinstance(fees, list):
            for entry in fees:
                if isinstance(entry, dict) and entry.get("cost") is not None:
                    fee_cost = float(entry["cost"])
                    if not math.isfinite(fee_cost):
                        return {"ok": False, "reason": "nonfinite_fee", "fee": fee_cost}
                    if fee_cost < 0:
                        return {"ok": False, "reason": "negative_fee", "fee": fee_cost}
                    fee_costs.append(fee_cost)
        if fee_costs and cost is not None:
            total_fee = sum(fee_costs)
            fee_tolerance = max(1e-12, abs(cost) * tolerance_pct)
            if total_fee > cost + fee_tolerance:
                return {"ok": False, "reason": "fee_exceeds_order_cost", "fee": total_fee, "cost": cost}
        if not math.isfinite(float(filled_qty)) or not math.isfinite(float(average_price)):
            return {"ok": False, "reason": "nonfinite_fill_or_price"}
        if float(filled_qty) < 0 or float(average_price) < 0:
            return {"ok": False, "reason": "negative_fill_or_price"}
        expected = float(filled_qty) * float(average_price)
        return {
            "ok": True,
            "reported_cost": cost,
            "expected_cost": expected,
            "relative_tolerance": tolerance_pct,
        }

    def _exchange_for_pending_order(self, item: dict):
        """Resolve a pending order to its recorded venue without cross-venue fallback."""
        exchanges = getattr(self, "exchanges", {}) or {}
        venue_id = str(item.get("venue_id") or "").strip()
        if venue_id:
            exchange = exchanges.get(venue_id)
            if exchange is None:
                named_matches = [
                    candidate for candidate in exchanges.values()
                    if str(getattr(candidate, "name", "")).strip() == venue_id
                ]
                if len(named_matches) == 1:
                    exchange = named_matches[0]
            if exchange is None:
                self._enter_safe_state("critical_runtime_condition")
                self.log("PENDING_ORDER_VENUE_UNAVAILABLE", {
                    "venue_id": venue_id,
                    "symbol": str(item.get("symbol") or ""),
                    "order_id": str(item.get("external_id") or ""),
                })
            return exchange
        return self._main_exchange()

    def _prepare_reconciliation_transaction(self, order_id: str, item: dict, side: str, delta: float, delta_notional: float, fee_delta: float, final_filled: float, cumulative_fee: float, cumulative_notional: float, fill_price: float, terminal: bool) -> str:
        import copy
        positions = copy.deepcopy(self.state.open_positions)
        pending = copy.deepcopy(self.state.pending_orders)
        financial = copy.deepcopy(self.state.financial_account)
        risk_obj = getattr(self, "risk", None)
        risk_state = risk_obj.snapshot_state() if risk_obj is not None and hasattr(risk_obj, "snapshot_state") else {"pnl_today_pct": float(getattr(self.state, "pnl_today_pct", 0.0)), "pnl_week_pct": float(getattr(self.state, "pnl_week_pct", 0.0)), "symbol_loss_streak": {}}
        ledger_records = []
        symbol = str(item["symbol"])
        position = positions.get(symbol)
        if delta > 1e-12 and side == "buy":
            if position is None:
                stop_pct = float(item.get("stop_pct") or 0.0)
                tp_pct = float(item.get("take_profit_pct") or 0.0)
                if stop_pct <= 0 or tp_pct <= 0:
                    raise ValueError("missing_buy_recovery_risk_metadata")
                positions[symbol] = Position(str(item.get("exchange") or ""), symbol, fill_price, delta, fill_price * (1 - stop_pct), fill_price * (1 + tp_pct), float(item.get("created_ts") or time.time()), fee_delta)
            else:
                old_qty = position.qty
                position.qty = old_qty + delta
                position.entry = ((position.entry * old_qty) + (fill_price * delta)) / position.qty
                position.entry_fee += fee_delta
        elif delta > 1e-12 and side == "sell":
            if position is None or delta > position.qty + 1e-12:
                raise ValueError("reconciliation_sell_exceeds_position")
            allocated = position.entry_fee * (delta / position.qty) if position.qty > 0 else 0.0
            pnl_pct = ((fill_price - position.entry) * delta - allocated - fee_delta) / (position.entry * delta) if position.entry > 0 and delta > 0 else 0.0
            risk_state["pnl_today_pct"] = float(risk_state.get("pnl_today_pct", 0.0)) + pnl_pct
            risk_state["pnl_week_pct"] = float(risk_state.get("pnl_week_pct", 0.0)) + pnl_pct
            streaks = dict(risk_state.get("symbol_loss_streak", {}))
            streaks[symbol] = int(streaks.get(symbol, 0)) + 1 if pnl_pct < 0 else 0
            risk_state["symbol_loss_streak"] = streaks
            entry = position.entry
            position.qty -= delta
            position.entry_fee = max(0.0, position.entry_fee - allocated)
            if position.qty <= 1e-12:
                positions.pop(symbol, None)
            ledger_records.append({"reconciliation_key": f"pending:{order_id}:{final_filled:.12g}:{cumulative_fee:.12g}:{cumulative_notional:.12g}", "record": {"exchange": str(item.get("exchange") or ""), "symbol": symbol, "side": "close", "qty": delta, "entry": entry, "exit": fill_price, "fees": allocated + fee_delta, "pnl_pct": pnl_pct, "reason": "reconciled_pending_order"}})
        elif delta > 1e-12:
            raise ValueError("unknown_reconciliation_side")
        if delta > 1e-12 and not getattr(self, "paper", False):
            base = symbol.split("/", 1)[0]
            flows = financial.setdefault("base_flow", {})
            flows[base] = float(flows.get(base, 0.0) or 0.0) + (delta if side == "buy" else -delta)
            quote = float(financial.get("quote_flow", 0.0) or 0.0)
            financial["quote_flow"] = quote - delta_notional - fee_delta if side == "buy" else quote + delta_notional - fee_delta
        item2 = dict(item)
        item2.update({"known_filled_qty": final_filled, "known_fee": cumulative_fee, "known_quote_notional": cumulative_notional, "known_fill_price": fill_price})
        if terminal:
            pending.pop(order_id, None)
        else:
            pending[order_id] = item2
        order_manager = getattr(self, "order_manager", None)
        order_guards = order_manager.export_order_guards() if order_manager is not None else {}
        target = {"positions": {k: asdict(v) for k, v in sorted(positions.items())}, "pending_orders": dict(sorted(pending.items())), "order_guards": order_guards, "execution_intents": dict(self.state.execution_intents), "financial_account": financial, "risk_state": risk_state}
        recovery_prepare = getattr(getattr(self, "recovery", None), "prepare_reconciliation", None)
        if callable(recovery_prepare):
            return recovery_prepare(target, ledger_records)
        transaction_id = f"legacy-{order_id}-{time.time_ns()}"
        self._legacy_reconciliation_target = target
        self._legacy_reconciliation_ledger = ledger_records
        return transaction_id

    def _reconcile_pending_orders(self) -> None:
        """Reconcile exchange fills idempotently, including partial fills and fees."""
        for order_id, item in list(self.state.pending_orders.items()):
            exchange = self._exchange_for_pending_order(item)
            if exchange is None:
                continue
            symbol = str(item.get("symbol", ""))
            if not order_id or not symbol:
                continue
            try:
                try:
                    client_order_id = str(item.get("client_order_id") or "").strip()
                    if item.get("browser_execution") and client_order_id and order_id.startswith("browser-client:"):
                        raw = exchange.fetch_order_by_client_order_id(client_order_id, symbol)
                        self.log("BROWSER_PENDING_ORDER_RESOLVED_BY_CLIENT_ID", {
                            "order_id": order_id, "symbol": symbol,
                            "client_order_id": client_order_id,
                        })
                    else:
                        raw = exchange.fetch_order(order_id, symbol)
                except Exception as fetch_exc:
                    # Browser submissions have a durable client-order id. If the
                    # browser's external id is not accepted by the exchange's
                    # fetch_order endpoint, resolve it through the client-order
                    # lookup before declaring the order unreconciled.
                    client_order_id = str(item.get("client_order_id") or "").strip()
                    if not item.get("browser_execution") or not client_order_id:
                        raise
                    try:
                        raw = exchange.fetch_order_by_client_order_id(client_order_id, symbol)
                        self.log("BROWSER_PENDING_ORDER_RESOLVED_BY_CLIENT_ID", {
                            "order_id": order_id, "symbol": symbol,
                            "client_order_id": client_order_id,
                        })
                    except (NotImplementedError, LookupError):
                        raise fetch_exc
                expected_client_id = str(item.get("client_order_id") or "").strip()
                returned_client_id = str(raw.get("clientOrderId") or raw.get("client_order_id") or "").strip()
                if expected_client_id and returned_client_id != expected_client_id:
                    self._enter_safe_state("critical_runtime_condition")
                    self.log("PENDING_ORDER_IDENTITY_MISMATCH", {
                        "order_id": order_id,
                        "symbol": symbol,
                        "expected_client_order_id": expected_client_id,
                        "returned_client_order_id": returned_client_id,
                    })
                    continue

                returned_symbol = str(raw.get("symbol") or "").strip()
                expected_side = str(item.get("side") or "").lower()
                returned_side = str(raw.get("side") or "").lower()
                if returned_symbol and returned_symbol != symbol:
                    self._enter_safe_state("critical_runtime_condition")
                    self.log("PENDING_ORDER_SYMBOL_MISMATCH", {
                        "order_id": order_id, "expected_symbol": symbol,
                        "returned_symbol": returned_symbol,
                    })
                    continue
                if returned_side and expected_side and returned_side != expected_side:
                    self._enter_safe_state("critical_runtime_condition")
                    self.log("PENDING_ORDER_SIDE_MISMATCH", {
                        "order_id": order_id, "expected_side": expected_side,
                        "returned_side": returned_side,
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

                # A terminal status does not prove zero fills when the venue
                # omits the cumulative filled quantity. Never discard such an
                # order or advance accounting on an absent/invalid fill field.
                if "filled" not in raw or raw.get("filled") is None:
                    self._enter_safe_state("critical_runtime_condition")
                    self.log("PENDING_ORDER_FILL_QUANTITY_MISSING", {
                        "order_id": order_id, "symbol": symbol, "status": status,
                    })
                    continue
                try:
                    final_filled = float(raw["filled"])
                except (TypeError, ValueError, OverflowError):
                    final_filled = float("nan")
                if not math.isfinite(final_filled):
                    self._enter_safe_state("critical_runtime_condition")
                    self.log("PENDING_ORDER_FILL_QUANTITY_INVALID", {
                        "order_id": order_id, "symbol": symbol,
                        "reported_filled_qty": raw.get("filled"),
                    })
                    continue
                known_filled = float(item.get("known_filled_qty") or 0.0)
                requested_qty = float(item.get("requested_qty") or 0.0)
                side = expected_side

                tolerance = max(1e-12, requested_qty * 1e-9)
                if final_filled < -tolerance or final_filled > requested_qty + tolerance:
                    self._enter_safe_state("critical_runtime_condition")
                    self.log("PENDING_ORDER_FILL_QUANTITY_INVALID", {
                        "order_id": order_id, "symbol": symbol,
                        "requested_qty": requested_qty,
                        "reported_filled_qty": final_filled,
                    })
                    continue
                if final_filled + tolerance < known_filled:
                    self._enter_safe_state("critical_runtime_condition")
                    self.log("PENDING_ORDER_FILL_REGRESSION", {
                        "order_id": order_id, "symbol": symbol,
                        "known_filled_qty": known_filled,
                        "reported_filled_qty": final_filled,
                    })
                    continue

                delta = max(0.0, final_filled - known_filled)
                cumulative_fee = self._extract_cumulative_quote_fee(raw, symbol)
                known_fee = float(item.get("known_fee") or 0.0)
                if cumulative_fee + tolerance < known_fee:
                    self._enter_safe_state("critical_runtime_condition")
                    self.log("PENDING_ORDER_FEE_REGRESSION", {
                        "order_id": order_id, "symbol": symbol,
                        "known_fee": known_fee,
                        "reported_fee": cumulative_fee,
                    })
                    continue
                fee_delta = max(0.0, cumulative_fee - known_fee)
                financial = self._validate_order_financial_invariant(
                    raw,
                    symbol,
                    final_filled,
                    float(raw.get("average") or raw.get("price") or item.get("known_fill_price") or 0.0),
                )
                self.state.financial_reconciliation = {
                    "order_id": order_id,
                    "symbol": symbol,
                    **financial,
                    "checked_at": time.time(),
                }
                if not financial.get("ok", False):
                    self._enter_safe_state("critical_runtime_condition")
                    self.log("PENDING_ORDER_FINANCIAL_INVARIANT_BLOCKED", self.state.financial_reconciliation)
                    continue
                cumulative_notional = float(
                    financial.get("reported_cost")
                    if financial.get("reported_cost") is not None
                    else financial.get("expected_cost") or 0.0
                )
                known_notional = float(item.get("known_quote_notional") or 0.0)
                if known_notional <= 0.0 and known_filled > 0.0:
                    known_price = float(item.get("known_fill_price") or 0.0)
                    if known_price > 0.0:
                        known_notional = known_filled * known_price
                tolerance_notional = max(
                    1e-12,
                    abs(cumulative_notional) * float(financial.get("relative_tolerance") or 0.002),
                )
                if cumulative_notional + tolerance_notional < known_notional:
                    self._enter_safe_state("critical_runtime_condition")
                    self.log("PENDING_ORDER_NOTIONAL_REGRESSION", {"order_id": order_id, "symbol": symbol})
                    continue
                delta_notional = max(0.0, cumulative_notional - known_notional)

                if delta > 1e-12:
                    position = self.state.open_positions.get(symbol)
                    if delta_notional <= 0:
                        self._enter_safe_state("critical_runtime_condition")
                        self.log("PENDING_ORDER_MISSING_INCREMENTAL_NOTIONAL", {
                            "order_id": order_id, "symbol": symbol, "delta_qty": delta
                        })
                        continue
                    fill_price = delta_notional / delta
                    if fill_price <= 0:
                        self._enter_safe_state("critical_runtime_condition")
                        self.log("MANUAL_RECONCILIATION_REQUIRED", {
                            "order_id": order_id, "symbol": symbol, "side": side,
                            "known_filled_qty": known_filled, "final_filled_qty": final_filled,
                            "delta_qty": delta,
                        })
                        continue

                if delta > 1e-12 and delta_notional <= 0:
                    self._enter_safe_state("critical_runtime_condition")
                    self.log("PENDING_ORDER_MISSING_INCREMENTAL_NOTIONAL", {
                        "order_id": order_id, "symbol": symbol, "delta_qty": delta
                    })
                    continue
                if delta > 1e-12:
                    fill_price = delta_notional / delta
                    if fill_price <= 0:
                        self._enter_safe_state("critical_runtime_condition")
                        self.log("MANUAL_RECONCILIATION_REQUIRED", {
                            "order_id": order_id, "symbol": symbol, "side": side,
                            "known_filled_qty": known_filled, "final_filled_qty": final_filled,
                            "delta_qty": delta,
                        })
                        continue
                else:
                    fill_price = float(
                        raw.get("average") or raw.get("price") or item.get("known_fill_price") or 0.0
                    )
                try:
                    reconciliation_transaction = self._prepare_reconciliation_transaction(
                        order_id, item, side, delta, delta_notional, fee_delta, final_filled,
                        cumulative_fee, cumulative_notional, fill_price, terminal,
                    )
                except ValueError as prep_exc:
                    self._enter_safe_state("critical_runtime_condition")
                    self.log("MANUAL_RECONCILIATION_REQUIRED", {
                        "order_id": order_id, "symbol": symbol, "side": side,
                        "reason": str(prep_exc),
                    })
                    continue
                recovery_obj = getattr(self, "recovery", None)
                durable_prepare = callable(getattr(recovery_obj, "prepare_reconciliation", None))
                if durable_prepare:
                    journal = recovery_obj.load_reconciliation_journal()
                    if journal is None or str(journal.get("transaction_id")) != str(reconciliation_transaction):
                        raise RuntimeError("reconciliation journal disappeared before commit")
                    recovery_obj.commit_reconciliation(reconciliation_transaction)
                    for ledger_entry in journal.get("ledger_records", []):
                        record = dict(ledger_entry.get("record") or {})
                        key = str(ledger_entry.get("reconciliation_key") or "")
                        idempotent = getattr(self.ledger, "trade_idempotent", None)
                        if callable(idempotent):
                            idempotent(record, key)
                        else:
                            self.ledger.trade(record)
                    recovery_obj.clear_reconciliation()
                    committed = recovery_obj.load_state()
                    self.state.pending_orders = dict(committed.get("pending_orders", {}))
                    self.state.financial_account = dict(committed.get("financial_account", {}))
                    self.state.open_positions = {
                        restored_symbol: Position(**restored_data)
                        for restored_symbol, restored_data in dict(committed.get("positions", {})).items()
                    }
                    risk_obj = getattr(self, "risk", None)
                    if risk_obj is not None and committed.get("risk_state"):
                        risk_obj.restore_state(committed["risk_state"])
                else:
                    committed = getattr(self, "_legacy_reconciliation_target", {})
                    self.state.pending_orders = dict(committed.get("pending_orders", {}))
                    self.state.financial_account = dict(committed.get("financial_account", {}))
                    self.state.open_positions = {
                        restored_symbol: Position(**restored_data)
                        for restored_symbol, restored_data in dict(committed.get("positions", {})).items()
                    }
                    for ledger_entry in getattr(self, "_legacy_reconciliation_ledger", []):
                        record = dict(ledger_entry.get("record") or {})
                        idempotent = getattr(self.ledger, "trade_idempotent", None)
                        if callable(idempotent):
                            idempotent(record, str(ledger_entry.get("reconciliation_key") or ""))
                        else:
                            self.ledger.trade(record)
                self.log("PENDING_ORDER_RECONCILED", {
                    "order_id": order_id, "symbol": symbol, "side": side, "status": status,
                    "terminal": terminal, "known_filled_qty": known_filled,
                    "final_filled_qty": final_filled, "delta_qty": delta,
                    "known_fee": known_fee, "final_fee": cumulative_fee, "fee_delta": fee_delta,
                })
            except Exception as exc:
                self._enter_safe_state("critical_runtime_condition")
                self.log("PENDING_ORDER_RECONCILE_ERROR", {
                    "order_id": order_id, "symbol": symbol, "error": str(exc)
                })
        if self.state.pending_orders:
            self._enter_safe_state("critical_runtime_condition")


    def _maybe_autonomous_real_promotion(self) -> bool:
        """Promote PAPER to REAL only when the full readiness contract is satisfied."""
        if self.mode != "PAPER":
            return False
        auto_cfg = self.config.get("autonomous_execution", {})
        if (
            not bool(auto_cfg.get("enabled", False))
            or not bool(auto_cfg.get("allow_real", False))
            or not bool(auto_cfg.get("auto_promote_real", False))
        ):
            return False
        # Re-evaluate on every cycle so the trader can wait for evidence rather
        # than relying on a stale readiness snapshot. This call is PAPER-only
        # and does not create orders.
        try:
            report = self.real_readiness_service.collect(self, target_mode="REAL")
        except Exception as exc:
            # Replace any previously displayed READY snapshot immediately. A
            # transient evaluation failure must never leave stale green status
            # in the cockpit while the promotion path is fail-closed.
            failed_report = {
                "ready": False,
                "status": "READINESS_EVALUATION_FAILED",
                "blockers": ["readiness_evaluation_failed"],
                "error": f"{type(exc).__name__}: {exc}",
                "promotion_attempted": False,
            }
            self.state.operational["real_readiness"] = failed_report
            self.log("AUTONOMOUS_REAL_READINESS_ERROR", {"error": str(exc)})
            return False
        self.state.operational["real_readiness"] = report
        if not bool(report.get("ready")) or not bool((report.get("paper_review") or {}).get("ready")):
            return False
        guard = getattr(self, "real_mode_guard", None)
        if guard is None:
            self.log("AUTONOMOUS_REAL_PROMOTION_BLOCKED", {"reason": "real_mode_guard_not_initialized"})
            return False
        gate = getattr(self, "execution_gate", None)
        if gate is None:
            gate = ExecutionGate()
            self.execution_gate = gate
        if bool(getattr(getattr(guard, "state", None), "human_authorized", False)) and not gate.human_authorized:
            gate.human_authorize()
        ok, reason = guard.authorize_from_readiness(report)
        if not ok:
            self.log("AUTONOMOUS_REAL_PROMOTION_BLOCKED", {"reason": reason})
            return False
        if not guard.consume()[0]:
            self.log("AUTONOMOUS_REAL_PROMOTION_BLOCKED", {"reason": "readiness authorization could not be consumed"})
            return False
        try:
            self.set_mode("REAL", real_authorized=True, autonomous=True)
            preflight = self.run_preflight()
            if not preflight.get("ok"):
                self._enter_real_fail_safe("autonomous_real_preflight_failed", preflight)
                return False
            reconciliation = self.reconcile_account_state()
            if not reconciliation.get("ok", False):
                self._enter_real_fail_safe("autonomous_real_reconciliation_failed", reconciliation)
                return False
            gate = getattr(self, "execution_gate", None)
            if gate is None:
                self._enter_real_fail_safe("execution_gate_missing")
                return False
            if gate.state == ExecutionState.SAFEGUARD_PAPER:
                recovery = gate.evaluate_recovery(
                    readiness_ok=bool(report.get("ready")) and bool((report.get("paper_review") or {}).get("ready")),
                    reconciliation_ok=bool(reconciliation.get("ok", False)),
                    timing_ok=bool((report.get("websocket_timing") or {}).get("eligible_for_economic_interpretation", False)) and bool((report.get("websocket_timing") or {}).get("fresh", False)),
                )
                if not recovery.allowed:
                    self._enter_real_fail_safe("execution_gate_recovery_blocked", {"reason": recovery.reason})
                    return False
                activation = gate.activate_real()
                if not activation.allowed:
                    self._enter_real_fail_safe("execution_gate_activation_blocked", {"reason": activation.reason})
                    return False
            elif gate.state != ExecutionState.REAL_ACTIVE:
                activation = gate.activate_real()
                if not activation.allowed:
                    self._enter_real_fail_safe("execution_gate_activation_blocked", {"reason": activation.reason})
                    return False
            self.real_operational = True
            self.state.status = "RUNNING"
            self.log("AUTONOMOUS_REAL_PROMOTION", {
                "reason": "real readiness gate satisfied",
                "readiness_status": report.get("status"),
            })
            return True
        except Exception as exc:
            self._enter_real_fail_safe("autonomous_real_promotion_error", {"error": str(exc)})
            return False

    def cycle(self) -> None:
        exchange = self._main_exchange()
        if exchange is None:
            self.log("NO_EXCHANGE_ENABLED")
            return
        self.refresh_human_bridge_operational_state()
        if not self._watchdog_gate(exchange):
            return
        if self.mode == "PAPER" and self._maybe_autonomous_real_promotion():
            exchange = self._main_exchange()
            if exchange is None:
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
                self._close_position(
                    exchange, position, price, signal.reason if signal else "stop/take-profit",
                    spreads.get(symbol, 0.0),
                    execution_checks={
                        "opportunity_ok": bool(price <= position.stop or price >= position.take_profit or (signal and signal.action == "SELL")),
                        "risk_ok": True,
                        "exchange_ok": bool(exchange) and str(getattr(exchange, "name", "")) in self.exchanges,
                        "stale_ok": self._ticker_is_fresh(ticker),
                    },
                )

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
            adaptive_cfg = self.config.get("risk", {}).get("adaptive_risk", {})
            adaptive_horizon = int(adaptive_cfg.get("horizon_seconds", 5))
            adaptive_notional, adaptive_snapshot = self.risk.adaptive_position_notional_auto(
                equity, signal.stop_pct, strategy_id="trend_ema_atr", symbol=symbol,
                regime=signal.regime, horizon_seconds=adaptive_horizon, action="BUY",
            )
            notional = min(decision.max_notional, adaptive_notional)
            self.log("ADAPTIVE_RISK_SIZING", {
                "symbol": symbol, "context_key": adaptive_snapshot.context_key,
                "multiplier": adaptive_snapshot.multiplier, "eligible": adaptive_snapshot.eligible,
                "reason": adaptive_snapshot.reason, "samples": adaptive_snapshot.samples,
            })
            if notional <= 0:
                continue

            current_exposure = sum(
                float(position.entry) * float(position.qty)
                for position in self.state.open_positions.values()
            )
            current_symbol_exposure = 0.0
            if symbol in self.state.open_positions:
                current_position = self.state.open_positions[symbol]
                current_symbol_exposure = float(current_position.entry) * float(current_position.qty)

            symbol_limit = self.config.get("symbol_limits", {}).get(symbol, {})
            risk_decision = self.risk.authorize_order(
                symbol,
                "BUY",
                equity=equity,
                proposed_notional=notional,
                current_exposure=current_exposure,
                current_symbol_exposure=current_symbol_exposure,
                current_open_positions=len(self.state.open_positions),
                max_open_positions=int(self.config["engine"]["max_open_positions"]),
                max_total_exposure_pct=float(self.config["engine"]["max_total_exposure_pct"]),
                max_symbol_exposure_pct=float(symbol_limit.get("max_exposure_pct", 0.10)),
                stop_pct=float(signal.stop_pct),
            )
            if not risk_decision.authorized:
                self.log("FINAL_RISK_BLOCK", {
                    "symbol": symbol,
                    "reason": risk_decision.reason,
                    "notional": notional,
                })
                continue

            qty = notional / price
            self._open_position(
                exchange, symbol, price, qty, signal.stop_pct, signal.take_profit_pct,
                signal.reason, spreads.get(symbol, 0.0),
                execution_checks={
                    "opportunity_ok": signal.action == "BUY" and scores.get(symbol, 0.0) > 0,
                    "risk_ok": bool(risk_decision.authorized),
                    "exchange_ok": bool(exchange) and str(getattr(exchange, "name", "")) in self.exchanges,
                    "stale_ok": self._ticker_is_fresh(ticker),
                },
            )

        self._persist_recovery()

    def _ticker_is_fresh(self, ticker: dict, *, now_ms: float | None = None) -> bool:
        """Fail closed when an execution ticker has no trustworthy timestamp."""
        if not isinstance(ticker, dict):
            return False
        try:
            timestamp = float(ticker.get("timestamp") or 0.0)
        except (TypeError, ValueError):
            return False
        if timestamp <= 0:
            return False
        quality_cfg = self.config.get("market_data_quality", {})
        max_age_seconds = max(0.1, float(quality_cfg.get("max_ticker_age_seconds", 10.0)))
        current_ms = float(now_ms if now_ms is not None else time.time() * 1000.0)
        age_ms = current_ms - timestamp
        return -2000.0 <= age_ms <= max_age_seconds * 1000.0

    def _open_position(
        self, exchange: CcxtExchangeClient, symbol: str, price: float, qty: float,
        stop_pct: float, tp_pct: float, reason: str, spread_pct: float = 0.0,
        execution_checks: dict | None = None,
    ) -> None:
        if not getattr(self, "paper", True):
            gate = getattr(self, "execution_gate", None)
            if gate is None:
                self._enter_real_fail_safe("execution_gate_missing")
                return
            checks = execution_checks if isinstance(execution_checks, dict) else {}
            decision = gate.can_submit(
                opportunity_ok=bool(checks.get("opportunity_ok", False)),
                risk_ok=bool(checks.get("risk_ok", False)),
                exchange_ok=bool(checks.get("exchange_ok", False)),
                stale_ok=bool(checks.get("stale_ok", False)),
            )
            if not decision.allowed:
                self.log("EXECUTION_GATE_BLOCKED_ORDER", {"symbol": symbol, "side": "buy", "state": decision.state.value, "reason": decision.reason})
                if (
                    decision.state != ExecutionState.REAL_ACTIVE
                    or not bool(checks.get("exchange_ok", False))
                    or not bool(checks.get("stale_ok", False))
                ):
                    self._enter_real_fail_safe("execution_gate_order_blocked", {"symbol": symbol, "reason": decision.reason})
                return
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
            self._enter_safe_state("critical_runtime_condition")
            self._persist_recovery()
            raise
        if result.status == "PENDING_OR_PARTIAL":
            self._enter_safe_state("critical_runtime_condition")
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
                "known_filled_qty": 0.0,
                "known_fill_price": result.price,
                "known_fee": 0.0,
                "known_quote_notional": 0.0,
                "created_ts": time.time(),
                "client_order_id": client_order_id,
                "stop_pct": stop_pct,
                "take_profit_pct": tp_pct,
                "reason": reason,
            }
            self._persist_recovery()
            self.state.execution_intents.pop(intent_id, None)
            self._persist_recovery()
            # Do not mutate positions from an unconfirmed partial/pending result.
            # _reconcile_pending_orders is the single source of truth for fills.
            return
        if not result.ok:
            self.state.execution_intents.pop(intent_id, None)
            self._persist_recovery()
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
        if result.status != "PENDING_OR_PARTIAL":
            self._record_financial_fill("buy", symbol, float(result.qty), float(result.qty) * float(result.price), float(result.fee))
        with self.lock:
            self.state.open_positions[symbol] = position
        self._persist_recovery()
        self.state.execution_intents.pop(intent_id, None)
        self._persist_recovery()
        self.log("POSITION_OPENED", {"symbol": symbol, "price": result.price, "qty": result.qty, "fee": result.fee, "reason": reason})

    def _close_position(
        self, exchange: CcxtExchangeClient, position: Position, price: float,
        reason: str, spread_pct: float = 0.0, execution_checks: dict | None = None,
    ) -> None:
        if not getattr(self, "paper", True):
            gate = getattr(self, "execution_gate", None)
            if gate is None:
                self._enter_real_fail_safe("execution_gate_missing")
                return
            checks = execution_checks if isinstance(execution_checks, dict) else {}
            decision = gate.can_submit(
                opportunity_ok=bool(checks.get("opportunity_ok", False)),
                risk_ok=bool(checks.get("risk_ok", False)),
                exchange_ok=bool(checks.get("exchange_ok", False)),
                stale_ok=bool(checks.get("stale_ok", False)),
            )
            if not decision.allowed:
                self.log("EXECUTION_GATE_BLOCKED_ORDER", {"symbol": position.symbol, "side": "sell", "state": decision.state.value, "reason": decision.reason})
                if (
                    decision.state != ExecutionState.REAL_ACTIVE
                    or not bool(checks.get("exchange_ok", False))
                    or not bool(checks.get("stale_ok", False))
                ):
                    self._enter_real_fail_safe("execution_gate_order_blocked", {"symbol": position.symbol, "reason": decision.reason})
                return
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
            self._enter_safe_state("critical_runtime_condition")
            self._persist_recovery()
            raise
        if result.status == "PENDING_OR_PARTIAL":
            self._enter_safe_state("critical_runtime_condition")
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
                "known_filled_qty": 0.0,
                "known_fill_price": result.price,
                "known_fee": 0.0,
                "known_quote_notional": 0.0,
                "created_ts": time.time(),
                "stop_pct": max(0.0, (position.entry - position.stop) / position.entry) if position.entry > 0 else 0.0,
                "take_profit_pct": max(0.0, (position.take_profit - position.entry) / position.entry) if position.entry > 0 else 0.0,
            }
            self._persist_recovery()
            self.state.execution_intents.pop(intent_id, None)
            self._persist_recovery()
            # Do not mutate positions from an unconfirmed partial/pending result.
            # _reconcile_pending_orders is the single source of truth for fills.
            return
        if not result.ok:
            self.state.execution_intents.pop(intent_id, None)
            self._persist_recovery()
            self.log("ORDER_REJECTED", {"symbol": position.symbol, "side": "sell", "reason": result.reason})
            return
        filled_qty = min(float(result.qty), float(position.qty))
        if filled_qty <= 0:
            return
        if result.status != "PENDING_OR_PARTIAL":
            self._record_financial_fill("sell", position.symbol, filled_qty, float(result.price) * filled_qty, float(result.fee))
        allocated_entry_fee = position.entry_fee * (filled_qty / position.qty) if position.qty > 0 else 0.0
        notional = result.price * filled_qty
        gross_pnl = (result.price - position.entry) * filled_qty
        net_pnl = gross_pnl - allocated_entry_fee - result.fee
        pnl_pct = net_pnl / (position.entry * filled_qty) if position.entry and filled_qty > 0 else 0.0
        self.risk.record_trade_result(position.symbol, pnl_pct)
        risk_state = getattr(self.risk, "state", None)
        drawdown = float(getattr(risk_state, "drawdown_pct", 0.0))
        self.champion.record("trend_ema_atr", pnl_pct, drawdown, live=True)
        remaining_qty = max(0.0, position.qty - filled_qty)
        lock = getattr(self, "lock", None)
        if lock is None:
            from contextlib import nullcontext
            lock = nullcontext()
        with lock:
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
        self.state.execution_intents.pop(intent_id, None)
        self._persist_recovery()
        self.log("POSITION_PARTIALLY_CLOSED" if remaining_qty > 1e-12 else "POSITION_CLOSED", {
            "symbol": position.symbol,
            "filled_qty": filled_qty,
            "remaining_qty": remaining_qty,
            "pnl_pct": pnl_pct,
            "fee": allocated_entry_fee + result.fee,
            "reason": reason,
        })