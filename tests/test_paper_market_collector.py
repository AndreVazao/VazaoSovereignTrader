from __future__ import annotations

from pathlib import Path

from PC_ENGINE.core.strategy import Signal
from PC_ENGINE.services.paper_market_collector import PaperMarketCollector
from PC_ENGINE.radar.evidence_ledger import EvidenceLedger, EvidenceLedgerRecord, EvidencePlaneSummary


class FakeStrategy:
    def analyse(self, symbol, ohlcv, spread_pct=0.0):
        return Signal("BUY", "TREND_UP", 0.8, "test", 0.01, 0.02)


def _ohlcv(count: int = 40):
    rows = []
    price = 100.0
    for i in range(count):
        price += 0.2
        rows.append([i * 60_000, price - 0.1, price + 0.2, price - 0.2, price, 1000.0])
    return rows


def test_collector_records_market_state(tmp_path: Path):
    settings = {
        "interval_seconds": 5,
        "polling_exchanges": [],
        "data_dir": str(tmp_path),
        "candlestick": {"enabled": True, "min_confidence": 0.70},
        "confluence": {
            "enabled": True,
            "observational_only": True,
            "paper_only": True,
            "data_dir": str(tmp_path),
            "derivatives": {"enabled": False, "observational_only": True},
        },
    }

    collector = PaperMarketCollector(
        settings=settings,
        symbols=["BTC/USDT"],
        ohlcv_fetcher=lambda symbol, timeframe, limit: _ohlcv(),
        strategy=FakeStrategy(),
    )
    try:
        recorded = collector.collect_once()
        assert recorded == 1
        state_path = tmp_path / "market_states.jsonl"
        assert state_path.exists()
        assert '"symbol":"BTC/USDT"' in state_path.read_text(encoding="utf-8")
        assert collector.snapshot()["cycles"] == 1
    finally:
        collector.stop()


def test_collector_never_uses_order_interface(tmp_path: Path):
    settings = {
        "polling_exchanges": [],
        "data_dir": str(tmp_path),
        "confluence": {
            "data_dir": str(tmp_path),
            "derivatives": {"enabled": False, "observational_only": True},
        },
    }
    calls = []

    collector = PaperMarketCollector(
        settings=settings,
        symbols=["BTC/USDT"],
        ohlcv_fetcher=lambda symbol, timeframe, limit: _ohlcv(),
        strategy=FakeStrategy(),
    )
    try:
        collector.collect_once()
        assert calls == []
    finally:
        collector.stop()


def _evidence_record(ts: int, eligible: bool = True):
    plane = EvidencePlaneSummary(
        "durable", "PASS" if eligible else "FAIL", 30, 2, 2 if eligible else 1,
        5.0 if eligible else -1.0, 1.0 if eligible else -2.0,
        1.0 if eligible else -2.0, 1.0 if eligible else 0.0, 2,
    )
    return EvidenceLedger.with_digest(EvidenceLedgerRecord(
        created_at_ms=ts,
        candidate_id="cand", version="1", strategy="momentum",
        symbol="BTC/USDT", regime="BULL", horizon_ms=5000,
        eligible=eligible, reason="ok" if eligible else "failed",
        reason_codes=() if eligible else ("failed",),
        data_start_ms=ts - 10000, data_end_ms=ts,
        state_count=30, outcome_count=30,
        durable_outcome=plane, chronological_oos=plane,
        source_digest="0" * 64,
    ))


def test_collector_refreshes_and_persists_evidence_learning(tmp_path: Path):
    ledger = tmp_path / "evidence_ledger.jsonl"
    EvidenceLedger.append(ledger, _evidence_record(1000, True))
    EvidenceLedger.append(ledger, _evidence_record(2000, False))
    settings = {
        "polling_exchanges": [],
        "data_dir": str(tmp_path),
        "learning_interval_cycles": 1,
        "evidence": {
            "ledger_path": str(ledger),
            "learning_loop": {
                "enabled": True,
                "recent_records": 1,
                "degradation_threshold": 0.20,
                "snapshot_path": str(tmp_path / "learning_snapshot.json"),
            },
        },
        "confluence": {
            "data_dir": str(tmp_path),
            "derivatives": {"enabled": False, "observational_only": True},
        },
    }
    collector = PaperMarketCollector(
        settings=settings,
        symbols=["BTC/USDT"],
        ohlcv_fetcher=lambda symbol, timeframe, limit: _ohlcv(),
        strategy=FakeStrategy(),
    )
    try:
        collector.collect_once()
        snapshot = collector.snapshot()["evidence_learning"]
        assert snapshot["snapshot"]["degradation_detected"]
        assert snapshot["snapshot"]["actions"][0]["action"] == "INVESTIGATE"
        assert Path(snapshot["snapshot_path"]).exists()
    finally:
        collector.stop()


def test_collector_fails_closed_on_tampered_evidence_learning_ledger(tmp_path: Path):
    ledger = tmp_path / "evidence_ledger.jsonl"
    EvidenceLedger.append(ledger, _evidence_record(1000, True))
    raw = ledger.read_text(encoding="utf-8").replace('"eligible":true', '"eligible":false')
    ledger.write_text(raw, encoding="utf-8")
    settings = {
        "polling_exchanges": [],
        "data_dir": str(tmp_path),
        "learning_interval_cycles": 1,
        "evidence": {"ledger_path": str(ledger)},
        "confluence": {
            "data_dir": str(tmp_path),
            "derivatives": {"enabled": False, "observational_only": True},
        },
    }
    collector = PaperMarketCollector(
        settings=settings,
        symbols=["BTC/USDT"],
        ohlcv_fetcher=lambda symbol, timeframe, limit: _ohlcv(),
        strategy=FakeStrategy(),
    )
    try:
        collector.collect_once()
        state = collector.snapshot()["evidence_learning"]
        assert state["errors"] == 1
        assert state["snapshot"] is None
        assert not Path(state["snapshot_path"]).exists()
    finally:
        collector.stop()
