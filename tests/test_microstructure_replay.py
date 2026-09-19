from __future__ import annotations

import json

from PC_ENGINE.replay.microstructure_replay import MicrostructureReplay, MicrostructureReplayConfig
from PC_ENGINE.paper.microstructure import BookLevel, OrderBookSnapshot, OrderBookSimulator


def test_book_fills_and_partials():
    book = OrderBookSnapshot(
        "test", "BTC/USDT", 1.0,
        bids=(BookLevel(99.0, 1.0),),
        asks=(BookLevel(101.0, 0.5), BookLevel(102.0, 0.5)),
    )
    sim = OrderBookSimulator()
    result = sim.simulate_market_order(book, side="BUY", quantity=0.75)
    assert result.status == "FILLED"
    assert result.filled_qty == 0.75
    assert result.average_price > 101.0


def test_missing_input(tmp_path):
    report = MicrostructureReplay(MicrostructureReplayConfig(
        input_path=str(tmp_path / "missing.jsonl"),
        output_path=str(tmp_path / "out.json"),
    )).run()
    assert report.status == "EMPTY"
    assert report.events_loaded == 0
