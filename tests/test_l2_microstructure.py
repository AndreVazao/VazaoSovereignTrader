from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from PC_ENGINE.replay.l2_microstructure import L2MicrostructureReplay


class L2MicrostructureReplayTests(unittest.TestCase):
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
