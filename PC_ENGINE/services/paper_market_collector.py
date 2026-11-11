from __future__ import annotations

import hashlib
import json
from pathlib import Path
import threading
import time
from typing import Callable

from PC_ENGINE.core.candlestick_patterns import CandlestickPatternEngine
from PC_ENGINE.core.preflight import validate_ohlcv_rows
from PC_ENGINE.core.confluence_runtime import PaperConfluenceRuntime
from PC_ENGINE.learning.state_signature import StateSignatureLearningEngine
from PC_ENGINE.learning.shared_memory import VersionConflict
from PC_ENGINE.learning.sqlite_memory import SQLiteLearningMemory
from PC_ENGINE.learning.evidence_learning_loop import PaperEvidenceLearningLoop
from PC_ENGINE.radar.evidence_ledger import EvidenceLedger
from PC_ENGINE.radar.paper_evidence_ledger_builder import PaperEvidenceLedgerBuilder
from PC_ENGINE.radar.market_radar import MarketRadar
from PC_ENGINE.radar.market_state import MarketStateStore
from PC_ENGINE.radar.state_outcomes import StateOutcomeEngine
from PC_ENGINE.radar.champion_challenger import CandidateSpec
from PC_ENGINE.radar.paper_champion_runtime import PaperChampionRuntime


class PaperMarketCollector:
    """Continuous PAPER-only market-state collector and outcome learner.

    Collects public cross-exchange observations and feeds the existing
    confluence/state pipeline. It never submits orders and never changes
    trading mode.
    """

    def __init__(
        self,
        settings: dict,
        symbols: list[str],
        ohlcv_fetcher: Callable[[str, str, int], list[list[float]]],
        strategy,
        on_error: Callable[[str, dict], None] | None = None,
        learning_memory: SQLiteLearningMemory | None = None,
        resource_manager=None,
    ) -> None:
        self.settings = settings
        self.symbols = list(dict.fromkeys(symbols))
        self.ohlcv_fetcher = ohlcv_fetcher
        self.strategy = strategy
        self.on_error = on_error
        self.learning_memory = learning_memory
        self.resource_manager = resource_manager
        adaptive_cfg = dict(settings.get("adaptive_resources", {}))
        self.adaptive_enabled = bool(adaptive_cfg.get("enabled", resource_manager is not None))
        self.resource_refresh_interval_seconds = max(5.0, float(adaptive_cfg.get("refresh_interval_seconds", 60.0)))
        configured_interval = max(2.0, float(settings.get("interval_seconds", 5.0)))
        self.compact_interval_seconds = max(configured_interval, float(adaptive_cfg.get("compact_interval_seconds", 15.0)))
        self.compact_learning_multiplier = max(1, int(adaptive_cfg.get("compact_learning_interval_multiplier", 4)))
        self._resource_last_refresh = 0.0
        self._resource_status = {"state": "UNINITIALIZED", "profile": "BALANCED"}
        self._resource_policy = None
        self._effective_interval_seconds = configured_interval
        self.durable_learning_persisted = 0
        self.durable_learning_duplicates = 0
        self.durable_learning_errors = 0
        self.durable_learning_last_error: str | None = None
        self.interval_seconds = max(2.0, float(settings.get("interval_seconds", 5.0)))
        self.timeframe = str(settings.get("timeframe", "1m"))
        self.candles_limit = max(30, int(settings.get("candles_limit", 120)))
        self.data_dir = Path(settings.get("data_dir", "PC_ENGINE/data/radar"))
        self.request_timeout_ms = max(1000, min(60000, int(settings.get("request_timeout_ms", 8000))))
        self.shutdown_timeout_seconds = max(
            1.0,
            float(settings.get("shutdown_timeout_seconds", self.request_timeout_ms / 1000.0 + 2.0)),
        )
        self.stop_event = threading.Event()
        self.stop_requested_at: float | None = None
        self.polling_exchanges = list(settings.get(
            "polling_exchanges",
            ["binance", "bingx", "okx", "bybit", "coinbase"],
        ))
        self.radar = MarketRadar(
            exchanges=self.polling_exchanges,
            symbols=self.symbols,
            data_dir=str(self.data_dir),
            request_timeout_ms=self.request_timeout_ms,
            stop_event=self.stop_event,
        )
        self._radar_closed = False
        self.confluence = PaperConfluenceRuntime(settings.get("confluence", {}))
        self.patterns = CandlestickPatternEngine(settings.get("candlestick", {}))
        self.thread: threading.Thread | None = None
        self.last_cycle_ms = 0
        self.cycles = 0
        self.errors = 0

        self.learning_interval_cycles = max(1, int(settings.get("learning_interval_cycles", 12)))
        self._effective_learning_interval_cycles = self.learning_interval_cycles
        self.learning_state_limit = max(100, int(settings.get("learning_state_limit", 5000)))
        self.learning_horizons_ms = tuple(
            int(x) for x in settings.get("learning_horizons_ms", (5000, 15000, 60000))
        )
        self.learning_min_samples = max(1, int(settings.get("learning_min_samples", 30)))
        self.learning_cost_bps = max(0.0, float(settings.get("learning_cost_bps", 28.0)))
        evidence_cfg = dict(settings.get("evidence", {}))
        learning_cfg = dict(evidence_cfg.get("learning_loop", {}))
        self.evidence_ledger_path = Path(
            evidence_cfg.get(
                "ledger_path",
                str(self.data_dir / "evidence_ledger.jsonl"),
            )
        )
        self.evidence_learning_recent_records = max(
            1, int(learning_cfg.get("recent_records", 20))
        )
        self.evidence_learning_threshold = max(
            0.0, min(1.0, float(learning_cfg.get("degradation_threshold", 0.20)))
        )
        self.evidence_learning_snapshot_path = Path(
            learning_cfg.get(
                "snapshot_path",
                str(self.data_dir / "evidence_learning_snapshot.json"),
            )
        )
        self.evidence_learning_enabled = bool(learning_cfg.get("enabled", True))
        self.evidence_ledger_builder = PaperEvidenceLedgerBuilder(settings)
        self.last_evidence_learning_snapshot: dict | None = None
        self.evidence_learning_errors = 0
        self.learning_path = Path(
            settings.get(
                "learning_path",
                str(self.data_dir / "state_signature_learning.jsonl"),
            )
        )
        self.outcome_path = Path(
            settings.get(
                "outcome_path",
                str(self.data_dir / "state_outcomes.jsonl"),
            )
        )

        self.state_store = MarketStateStore(str(self.data_dir))
        candidate_specs = []
        for raw in settings.get("champion_challenger", {}).get("candidates", []):
            if not isinstance(raw, dict):
                continue
            try:
                candidate_specs.append(
                    CandidateSpec(
                        candidate_id=str(raw["candidate_id"]),
                        version=str(raw["version"]),
                        strategy=str(raw["strategy"]),
                        configuration=tuple(
                            (str(key), str(value))
                            for key, value in dict(raw.get("configuration", {})).items()
                        ),
                        evidence_type=str(raw.get("evidence_type", "")),
                        evidence_name=str(raw.get("evidence_name", "")),
                        symbol=str(raw.get("symbol", "")),
                        regime=str(raw.get("regime", "")),
                        horizon_ms=int(raw.get("horizon_ms", 0)),
                    )
                )
            except (KeyError, TypeError, ValueError):
                continue
        self.champion_runtime = PaperChampionRuntime(
            candidate_specs,
            path=settings.get("champion_challenger", {}).get(
                "state_path",
                str(self.data_dir / "champion_challenger_states.jsonl"),
            ),
        )
        self.learning_cycles = 0
        self.outcome_cycles = 0
        self.last_learning_stats = 0
        self.last_outcome_stats = 0

    def start(self) -> None:
        if self.thread and self.thread.is_alive():
            return
        if self._radar_closed:
            self.radar = MarketRadar(
                exchanges=self.polling_exchanges,
                symbols=self.symbols,
                data_dir=str(self.data_dir),
                request_timeout_ms=self.request_timeout_ms,
                stop_event=self.stop_event,
            )
            self._radar_closed = False
        self.stop_requested_at = None
        self.stop_event.clear()
        self.thread = threading.Thread(
            target=self._loop,
            name="paper-market-collector",
            daemon=True,
        )
        self.thread.start()

    def stop(self) -> bool:
        """Stop collection; retain live thread/radar references after a timeout."""
        self.stop_requested_at = self.stop_requested_at or time.time()
        self.stop_event.set()
        thread = self.thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=self.shutdown_timeout_seconds)
        if thread is not None and thread.is_alive():
            return False
        if not self._radar_closed:
            self.radar.close()
            self._radar_closed = True
        self.thread = None
        return True

    def snapshot(self) -> dict:
        return {
            "running": bool(self.thread and self.thread.is_alive()),
            "shutdown": {
                "requested": self.stop_event.is_set(),
                "requested_at": self.stop_requested_at,
                "worker_alive": bool(self.thread and self.thread.is_alive()),
                "timeout_seconds": self.shutdown_timeout_seconds,
                "request_timeout_ms": self.request_timeout_ms,
                "radar_closed": self._radar_closed,
            },
            "interval_seconds": self.interval_seconds,
            "effective_interval_seconds": self._effective_interval_seconds,
            "adaptive_resources": dict(self._resource_status),
            "cycles": self.cycles,
            "errors": self.errors,
            "last_cycle_ms": self.last_cycle_ms,
            "data_dir": str(self.data_dir),
            "market_data_collection": self.radar.collection_metrics(),
            "learning_cycles": self.learning_cycles,
            "learning_interval_cycles": self.learning_interval_cycles,
            "learning_path": str(self.learning_path),
            "outcome_path": str(self.outcome_path),
            "outcome_cycles": self.outcome_cycles,
            "last_learning_stats": self.last_learning_stats,
            "last_outcome_stats": self.last_outcome_stats,
            "evidence_ledger_writer": {
                "enabled": self.evidence_ledger_builder.enabled,
                "interval_cycles": self.evidence_ledger_builder.interval_cycles,
                "min_states": self.evidence_ledger_builder.min_states,
                "path": str(self.evidence_ledger_builder.path),
            },
            "evidence_learning": {
                "enabled": self.evidence_learning_enabled,
                "ledger_path": str(self.evidence_ledger_path),
                "snapshot_path": str(self.evidence_learning_snapshot_path),
                "recent_records": self.evidence_learning_recent_records,
                "degradation_threshold": self.evidence_learning_threshold,
                "errors": self.evidence_learning_errors,
                "snapshot": self.last_evidence_learning_snapshot,
            },
            "durable_learning": {
                "enabled": self.learning_memory is not None,
                "persisted": self.durable_learning_persisted,
                "duplicates": self.durable_learning_duplicates,
                "errors": self.durable_learning_errors,
                "last_error": self.durable_learning_last_error,
                "status_policy": "unverified_only",
                "order_authority": False,
            },
            "champion_challenger": self.champion_runtime.snapshot(),
        }

    def _refresh_resource_policy(self, *, force: bool = False) -> dict:
        """Refresh host policy without changing market-data or trading permissions."""
        now = time.monotonic()
        if not self.adaptive_enabled or self.resource_manager is None:
            self._resource_status = {"state": "DISABLED", "profile": "BALANCED", "defer_heavy_jobs": False, "order_authority": False}
            self._effective_interval_seconds = self.interval_seconds
            self._effective_learning_interval_cycles = self.learning_interval_cycles
            return self._resource_status
        if not force and now - self._resource_last_refresh < self.resource_refresh_interval_seconds:
            return self._resource_status
        self._resource_last_refresh = now
        try:
            policy = self.resource_manager.refresh()
            self._resource_policy = policy
            compact = str(getattr(policy, "profile", "COMPACT")).upper() == "COMPACT"
            defer_heavy = bool(getattr(policy, "defer_heavy_jobs", compact))
            self._effective_interval_seconds = self.compact_interval_seconds if compact else self.interval_seconds
            self._effective_learning_interval_cycles = self.learning_interval_cycles * self.compact_learning_multiplier if defer_heavy else self.learning_interval_cycles
            status = self.resource_manager.status() if hasattr(self.resource_manager, "status") else {}
            self._resource_status = {"state": "READY", "profile": str(getattr(policy, "profile", "UNKNOWN")), "defer_heavy_jobs": defer_heavy, "effective_interval_seconds": self._effective_interval_seconds, "effective_learning_interval_cycles": self._effective_learning_interval_cycles, "snapshot": status.get("snapshot") if isinstance(status, dict) else None, "policy": policy.to_dict() if hasattr(policy, "to_dict") else {"profile": str(getattr(policy, "profile", "UNKNOWN")), "defer_heavy_jobs": defer_heavy}, "order_authority": False}
        except Exception as exc:
            self._resource_policy = None
            self._effective_interval_seconds = self.compact_interval_seconds
            self._effective_learning_interval_cycles = self.learning_interval_cycles * self.compact_learning_multiplier
            self._resource_status = {"state": "DEGRADED", "profile": "COMPACT", "defer_heavy_jobs": True, "effective_interval_seconds": self._effective_interval_seconds, "effective_learning_interval_cycles": self._effective_learning_interval_cycles, "error": type(exc).__name__, "order_authority": False}
        return self._resource_status

    def _report_error(self, message: str, data: dict) -> None:
        self.errors += 1
        if self.on_error:
            self.on_error(message, data)

    def _loop(self) -> None:
        while not self.stop_event.is_set():
            started = time.monotonic()
            try:
                self.collect_once()
            except Exception as exc:
                self._report_error("PAPER_COLLECTOR_ERROR", {"error": str(exc)})
            elapsed = time.monotonic() - started
            self.stop_event.wait(max(0.0, self._effective_interval_seconds - elapsed))

    def collect_once(self) -> int:
        self._refresh_resource_policy()
        if self.stop_event.is_set():
            return 0
        snapshots, _ = self.radar.snapshot(stop_event=self.stop_event)
        if self.stop_event.is_set():
            return 0
        prices = {snap.symbol: snap.price for snap in snapshots}
        pressure = self.radar.pressure(snapshots)
        recorded = 0

        for symbol in self.symbols:
            if self.stop_event.is_set():
                break
            try:
                ohlcv = self.ohlcv_fetcher(symbol, self.timeframe, self.candles_limit)
                if self.stop_event.is_set():
                    break
                quality_cfg = self.settings.get("market_data_quality", {})
                quality = validate_ohlcv_rows(
                    ohlcv,
                    max_gap_seconds=quality_cfg.get("max_gap_seconds"),
                    max_age_seconds=quality_cfg.get("max_age_seconds"),
                )
                if not quality.ok:
                    self._report_error(
                        "PAPER_MARKET_DATA_QUALITY_BLOCK",
                        {
                            "symbol": symbol,
                            "valid_rows": quality.valid_rows,
                            "errors": quality.errors[:10],
                        },
                    )
                    continue
                if quality.valid_rows < 30:
                    continue
                ticker_price = prices.get(symbol)
                if not ticker_price or ticker_price <= 0:
                    ticker_price = float(ohlcv[-1][4])
                signal = self.strategy.analyse(symbol, ohlcv, 0.0)
                pattern_bias, _, _ = self.patterns.evaluate(ohlcv)
                result = self.confluence.evaluate_and_record(
                    symbol=symbol,
                    price=ticker_price,
                    ohlcv=ohlcv,
                    technical_action=signal.action,
                    technical_strength=float(signal.strength),
                    pattern_bias=pattern_bias,
                    radar_pressure=float(pressure.get(symbol, 0.0)),
                    timeframes={self.timeframe: ohlcv},
                )
                state_snapshot = self.state_store.snapshot(symbol)
                if state_snapshot is not None:
                    self.champion_runtime.observe(
                        state_snapshot,
                        cost_context=self.settings.get("confluence", {}).get("cost_context"),
                        shared_risk_authorized=result.risk_authorized,
                    )
                recorded += 1
                if self.on_error and not result.recorded:
                    self.on_error("PAPER_STATE_NOT_RECORDED", {"symbol": symbol})
            except Exception as exc:
                self._report_error(
                    "PAPER_SYMBOL_COLLECTION_ERROR",
                    {"symbol": symbol, "error": str(exc)},
                )

        if self.stop_event.is_set():
            self.last_cycle_ms = int(time.time() * 1000)
            return recorded

        self.confluence.resolve_outcomes()
        self.cycles += 1
        if self.cycles % self._effective_learning_interval_cycles == 0:
            if not bool(self._resource_status.get("defer_heavy_jobs", False)):
                self._refresh_learning()
                self._refresh_evidence_ledger()
                self._refresh_evidence_learning()
        self.last_cycle_ms = int(time.time() * 1000)
        return recorded

    @staticmethod
    def _atomic_save(rows, path: Path) -> int:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(
                    json.dumps(row.__dict__, separators=(",", ":"), sort_keys=True)
                    + "\n"
                )
        tmp.replace(path)
        return len(rows)

    def _persist_durable_learning(self, kind: str, identity: dict, observation: dict) -> bool:
        """Upsert one owner-private PAPER learning fact without granting authority."""
        memory = self.learning_memory
        if memory is None:
            return False
        try:
            identity_json = json.dumps(
                identity, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
            )
            observation_json = json.dumps(
                observation, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
            )
            digest = hashlib.sha256(identity_json.encode("utf-8")).hexdigest()
            key = f"paper.market_state.{kind}.{digest}"
            value = {
                "schema_version": 1,
                "kind": kind,
                "identity": identity,
                "observation": json.loads(observation_json),
                "paper_only": True,
                "execution_authorized": False,
            }
            current = memory.get(key)
            if current is not None and current.value == value:
                self.durable_learning_duplicates += 1
                return True
            expected_version = current.version if current is not None else 0
            try:
                memory.put(
                    key=key,
                    value=value,
                    department="market_radar",
                    provenance=f"paper_market_collector:{kind}:v1",
                    status="unverified",
                    confidence=0.0,
                    expected_version=expected_version,
                )
            except VersionConflict:
                latest = memory.get(key)
                if latest is not None and latest.value == value:
                    self.durable_learning_duplicates += 1
                    return True
                memory.put(
                    key=key,
                    value=value,
                    department="market_radar",
                    provenance=f"paper_market_collector:{kind}:v1",
                    status="unverified",
                    confidence=0.0,
                    expected_version=latest.version if latest is not None else 0,
                )
            self.durable_learning_persisted += 1
            self.durable_learning_last_error = None
            return True
        except Exception as exc:
            self.durable_learning_errors += 1
            self.durable_learning_last_error = type(exc).__name__
            return False

    def _persist_learning_rows(self, kind: str, rows, identity_fields: tuple[str, ...]) -> int:
        persisted = 0
        for row in rows:
            observation = dict(row.__dict__)
            identity = {field: observation[field] for field in identity_fields}
            if self._persist_durable_learning(kind, identity, observation):
                persisted += 1
        return persisted

    def _persist_evidence_learning_snapshot(self, payload: dict) -> None:
        self._persist_durable_learning(
            "evidence_learning",
            {"scope": "latest_snapshot"},
            payload,
        )

    def _refresh_evidence_ledger(self) -> int:
        """Materialize current PAPER observations into the immutable evidence ledger."""
        try:
            states = self.state_store.recent(
                limit=self.evidence_ledger_builder.max_states
            )
            return self.evidence_ledger_builder.refresh(states)
        except (OSError, ValueError, TypeError, KeyError) as exc:
            self._report_error(
                "PAPER_EVIDENCE_LEDGER_WRITE_ERROR",
                {"ledger_path": str(self.evidence_ledger_builder.path), "error": str(exc)},
            )
            return 0

    def _refresh_evidence_learning(self) -> dict | None:
        """Evaluate the verified PAPER evidence ledger and persist its learning snapshot."""
        if not self.evidence_learning_enabled:
            return None
        try:
            records = EvidenceLedger.load(self.evidence_ledger_path)
            loop = PaperEvidenceLearningLoop(
                recent_records=self.evidence_learning_recent_records,
                degradation_threshold=self.evidence_learning_threshold,
            )
            snapshot = loop.evaluate(records)
            payload = snapshot.to_dict()
            self.evidence_learning_snapshot_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.evidence_learning_snapshot_path.with_suffix(
                self.evidence_learning_snapshot_path.suffix + ".tmp"
            )
            with tmp.open("w", encoding="utf-8") as handle:
                json.dump(payload, handle, separators=(",", ":"), sort_keys=True)
                handle.flush()
            tmp.replace(self.evidence_learning_snapshot_path)
            self.last_evidence_learning_snapshot = payload
            self._persist_evidence_learning_snapshot(payload)
            return payload
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            self.evidence_learning_errors += 1
            self._report_error(
                "PAPER_EVIDENCE_LEARNING_INVALID",
                {"ledger_path": str(self.evidence_ledger_path), "error": str(exc)},
            )
            return None

    def _refresh_learning(self) -> int:
        """Refresh descriptive signature and state-outcome evidence from PAPER data."""
        states = self.state_store.recent(limit=self.learning_state_limit)
        if len(states) < self.learning_min_samples:
            return 0

        signature_engine = StateSignatureLearningEngine(
            cost_bps=self.learning_cost_bps,
            min_samples=self.learning_min_samples,
        )
        signature_stats = signature_engine.evaluate(
            states,
            horizons_ms=self.learning_horizons_ms,
        )
        self.last_learning_stats = self._atomic_save(signature_stats, self.learning_path)
        self._persist_learning_rows(
            "state_signature", signature_stats, ("signature", "horizon_ms")
        )

        outcome_engine = StateOutcomeEngine(
            cost_bps=self.learning_cost_bps,
            min_samples=self.learning_min_samples,
        )
        outcome_stats = outcome_engine.evaluate(
            states,
            horizons_ms=self.learning_horizons_ms,
        )
        self.last_outcome_stats = self._atomic_save(outcome_stats, self.outcome_path)
        self._persist_learning_rows(
            "state_outcome", outcome_stats, ("symbol", "action", "regime", "horizon_ms")
        )

        self.learning_cycles += 1
        self.outcome_cycles += 1
        return self.last_learning_stats

