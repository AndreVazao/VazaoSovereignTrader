from __future__ import annotations

import json
from pathlib import Path

from PC_ENGINE.radar.evidence_ledger import EvidenceLedger
from PC_ENGINE.radar.paper_evidence_ledger_builder import PaperEvidenceLedgerBuilder


def _states(count: int = 400) -> list[dict]:
    rows = []
    base = 1_800_000_000_000
    for index in range(count):
        symbol = "BTC/USDT" if index % 2 == 0 else "ETH/USDT"
        regime = "TREND_UP" if (index // 2) % 2 == 0 else "TREND_DOWN"
        # Keep both symbols economically positive for the BUY evidence used by
        # this integration test while still exercising multiple regimes.
        price = 100.0 + index * 0.05
        rows.append(
            {
                "symbol": symbol,
                "timestamp_ms": base + index * 60_000,
                "price": price,
                "regime": regime,
                "strategy_evidence": {
                    "candlestick": {
                        "patterns": [
                            {"name": "BullishEngulfing", "direction": "BUY"}
                        ]
                    }
                },
            }
        )
    return rows


def test_paper_builder_materializes_a_validated_ledger(tmp_path: Path):
    ledger_path = tmp_path / "evidence.jsonl"
    settings = {
        "evidence": {
            "ledger_path": str(ledger_path),
            "ledger_min_states": 300,
            "ledger_train_size": 200,
            "ledger_test_size": 100,
            "ledger_step_size": 100,
            "ledger_horizons_ms": [5000],
            "ledger_costs_bps": [1, 2, 3],
            "ledger_min_cost_scenarios": 3,
        }
    }
    builder = PaperEvidenceLedgerBuilder(settings)

    written = builder.refresh(_states(), force=True)

    assert written > 0
    records = EvidenceLedger.load(ledger_path)
    assert records
    assert all(len(record.source_digest) == 64 for record in records)
    assert any(record.eligible for record in records)
    assert {record.symbol for record in records if record.eligible} >= {"BTC/USDT", "ETH/USDT"}
    assert {record.regime for record in records if record.eligible} >= {"TREND_UP", "TREND_DOWN"}

    # The persisted JSONL must remain readable by the canonical immutable ledger.
    assert len([line for line in ledger_path.read_text().splitlines() if line.strip()]) == len(records)


def test_paper_builder_does_not_duplicate_same_data_window(tmp_path: Path):
    ledger_path = tmp_path / "evidence.jsonl"
    settings = {
        "evidence": {
            "ledger_path": str(ledger_path),
            "ledger_min_states": 300,
            "ledger_train_size": 200,
            "ledger_test_size": 100,
            "ledger_step_size": 100,
            "ledger_horizons_ms": [5000],
            "ledger_costs_bps": [1, 2, 3],
            "ledger_min_cost_scenarios": 3,
        }
    }
    builder = PaperEvidenceLedgerBuilder(settings)
    states = _states()

    first = builder.refresh(states, force=True)
    second = builder.refresh(states, force=False)

    assert first > 0
    assert second == 0
