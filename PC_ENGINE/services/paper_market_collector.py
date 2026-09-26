from __future__ import annotations

import json
from pathlib import Path
import threading
import time
from typing import Callable

from PC_ENGINE.core.candlestick_patterns import CandlestickPatternEngine
from PC_ENGINE.core.preflight import validate_ohlcv_rows
from PC_ENGINE.core.confluence_runtime import PaperConfluenceRuntime
from PC_ENGINE.learning.state_signature import StateSignatureLearningEngine
from PC_ENGINE.learning.evidence_learning_loop import PaperEvidenceLearningLoop
from PC_ENGINE.radar.evidence_ledger import EvidenceLedger
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
    ) -> None:
        self.settings = settings
        self.symbols = list(dict.fromkeys(symbols))
        self.ohlcv_fetcher = ohlcv_fetcher
        self.strategy = strategy
        self.on_error = on_error
        self.interval_seconds = max(2.0, float(settings.get("interval_seconds", 5.0)))
        self.timeframe = str(settings.get("timeframe", "1m"))
        self.candles_limit = max(30, int(settings.get("candles_limit", 120)))
        self.data_dir = Path(settings.get("data_dir", "PC_ENGINE/data/radar"))
        self.radar = MarketRadar(
            exchanges=settings.get(
                "polling_exchanges",
                ["binance", "bingx", "okx", "bybit", "coinbase"],
            ),
            symbols=self.symbols,
            data_dir=str(self.data_dir),
        )
        self.confluence = PaperConfluenceRuntime(settings.get("confluence", {}))
        self.patterns = CandlestickPatternEngine(settings.get("candlestick", {}))
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None
        self.last_cycle_ms = 0
        self.cycles = 0
        self.errors = 0

        self.learning_interval_cycles = max(1, int(settings.get("learning_interval_cycles", 12)))
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
        self.stop_event.clear()
        self.thread = threading.Thread(
            target=self._loop,
            name="paper-market-collector",
            daemon=True,
        )
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=max(2.0, self.interval_seconds + 1.0))
        self.radar.close()
        self.thread = None

    def snapshot(self) -> dict:
        return {
            "running": bool(self.thread and self.thread.is_alive()),
            "interval_seconds": self.interval_seconds,
            "cycles": self.cycles,
            "errors": self.errors,
            "last_cycle_ms": self.last_cycle_ms,
            "data_dir": str(self.data_dir),
            "learning_cycles": self.learning_cycles,
            "learning_interval_cycles": self.learning_interval_cycles,
            "learning_path": str(self.learning_path),
            "outcome_path": str(self.outcome_path),
            "outcome_cycles": self.outcome_cycles,
            "last_learning_stats": self.last_learning_stats,
            "last_outcome_stats": self.last_outcome_stats,
            "evidence_learning": {
                "enabled": self.evidence_learning_enabled,
                "ledger_path": str(self.evidence_ledger_path),
                "snapshot_path": str(self.evidence_learning_snapshot_path),
                "recent_records": self.evidence_learning_recent_records,
                "degradation_threshold": self.evidence_learning_threshold,
                "errors": self.evidence_learning_errors,
                "snapshot": self.last_evidence_learning_snapshot,
            },
            "champion_challenger": self.champion_runtime.snapshot(),
        }

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
            self.stop_event.wait(max(0.0, self.interval_seconds - elapsed))

    def collect_once(self) -> int:
        snapshots, _ = self.radar.snapshot()
        prices = {snap.symbol: snap.price for snap in snapshots}
        pressure = self.radar.pressure(snapshots)
        recorded = 0

        for symbol in self.symbols:
            try:
                ohlcv = self.ohlcv_fetcher(symbol, self.timeframe, self.candles_limit)
                quality_cfg = self.settings.get("market_data_quality", {})
                quality = validate_ohlcv_rows(
                    ohlcv,
                    max_gap_seconds=quality_cfg.get("max_gap_seconds"),
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

        self.confluence.resolve_outcomes()
        self.cycles += 1
        if self.cycles % self.learning_interval_cycles == 0:
            self._refresh_learning()
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

        outcome_engine = StateOutcomeEngine(
            cost_bps=self.learning_cost_bps,
            min_samples=self.learning_min_samples,
        )
        outcome_stats = outcome_engine.evaluate(
            states,
            horizons_ms=self.learning_horizons_ms,
        )
        self.last_outcome_stats = self._atomic_save(outcome_stats, self.outcome_path)

        self.learning_cycles += 1
        self.outcome_cycles += 1
        return self.last_learning_stats

