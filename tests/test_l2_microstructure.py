from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from PC_ENGINE.replay.l2_microstructure import L2MicrostructureReplay


class L2MicrostructureReplayTests(unittest.TestCase):
    def test_loader_preserves_arrival_order_when_exchange_clock_is_out_of_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "events.jsonl"
            snapshot = {
                "event_id": "s1", "venue": "test", "symbol": "BTC/USDT",
                "event_type": "snapshot", "sequence": 10, "sequence_start": None,
                "provider_ts_ms": 2000, "exchange_ts_ms": 2000,
                "local_receive_ns": 1000, "local_receive_wall_ns": 1000,
                "bids": [{"price": 100.0, "quantity": 1.0}],
                "asks": [{"price": 101.0, "quantity": 1.0}], "raw_source": "test",
            }
            delta = {
                "event_id": "d2", "venue": "test", "symbol": "BTC/USDT",
                "event_type": "delta", "sequence": 11, "sequence_start": None,
                "provider_ts_ms": 1000, "exchange_ts_ms": 1000,
                "local_receive_ns": 2000, "local_receive_wall_ns": 2000,
                "bids": [{"price": 100.5, "quantity": 1.0}],
                "asks": [], "raw_source": "test",
            }
            source.write_text("\n".join(json.dumps(x) for x in (snapshot, delta)), encoding="utf-8")
            loaded = L2MicrostructureReplay._load(str(source))
            self.assertEqual([event.event_id for event in loaded], ["s1", "d2"])
            self.assertLess(L2MicrostructureReplay._time(loaded[0]), L2MicrostructureReplay._time(loaded[1]))

    def test_replay_uses_reconstructed_depth(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "events.jsonl"
            output = Path(tmp) / "report.json"
            rows = [
                {
                    "event_id": "s1", "venue": "test", "symbol": "BTC/USDT",
                    "event_type": "snapshot", "sequence": 1, "sequence_start": None,
                    "provider_ts_ms": 1, "exchange_ts_ms": 1,
                    "local_receive_ns": 1, "local_receive_wall_ns": 1,
                    "bids": [{"price": 100.0, "quantity": 0.5}],
                    "asks": [{"price": 101.0, "quantity": 0.25}],
                    "raw_source": "test",
                },
                {
                    "event_id": "d2", "venue": "test", "symbol": "BTC/USDT",
                    "event_type": "delta", "sequence": 2, "sequence_start": None,
                    "provider_ts_ms": 2, "exchange_ts_ms": 2,
                    "local_receive_ns": 2, "local_receive_wall_ns": 2,
                    "bids": [{"price": 99.0, "quantity": 1.0}],
                    "asks": [],
                    "raw_source": "test",
                },
            ]
            source.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
            report = L2MicrostructureReplay(str(source), str(output), 100.0).run()
            self.assertEqual(report.samples, 2)
            self.assertGreater(report.average_spread_bps or 0.0, 0.0)
            self.assertTrue(output.exists())


if __name__ == "__main__":
    unittest.main()
