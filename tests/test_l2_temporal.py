from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from PC_ENGINE.replay.l2_temporal import L2TemporalConfig, L2TemporalExecutableReplay


def row(event_id, venue, seq, ts, bid, ask, event_type="snapshot"):
    return {
        "event_id": event_id, "venue": venue, "symbol": "BTC/USDT",
        "event_type": event_type, "sequence": seq, "sequence_start": None,
        "provider_ts_ms": ts, "exchange_ts_ms": ts,
        "local_receive_ns": ts * 1_000_000, "local_receive_wall_ns": ts * 1_000_000,
        "bids": [{"price": bid, "quantity": 2.0}],
        "asks": [{"price": ask, "quantity": 2.0}],
        "raw_source": "test",
    }


class L2TemporalReplayTests(unittest.TestCase):
    def test_replay_executes_signal_through_depth(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "events.jsonl"
            output = Path(tmp) / "report.json"
            rows = [
                row("a1", "leader", 1, 1000, 100.0, 100.1),
                row("b1", "follower", 1, 1001, 100.0, 100.1),
                row("a2", "leader", 2, 1100, 100.0, 100.21, "delta"),
                row("b2", "follower", 2, 1150, 100.0, 100.22, "delta"),
                row("b3", "follower", 3, 1300, 100.2, 100.3, "delta"),
                row("b4", "follower", 4, 2200, 100.2, 100.3, "delta"),
            ]
            source.write_text("\n".join(json.dumps(x) for x in rows), encoding="utf-8")
            report = L2TemporalExecutableReplay(L2TemporalConfig(
                input_path=str(source), output_path=str(output),
                capital_per_trade=10.0, fee_bps=0.0, latency_ms=0.0,
                holding_ms=1000.0, min_move_bps=5.0, min_confidence=0.5,
            )).run()
            self.assertGreaterEqual(report.signals, 1)
            self.assertGreaterEqual(report.completed, 1)
            self.assertTrue(output.exists())


if __name__ == "__main__":
    unittest.main()
