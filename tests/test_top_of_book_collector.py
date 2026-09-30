from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from PC_ENGINE.tools.run_top_of_book_collector import _write_health


class TopOfBookCollectorHealthTests(unittest.TestCase):
    def test_health_file_is_atomic_and_paper_only(self) -> None:
        class FakeCollector:
            def snapshot(self):
                return {
                    "venue": "binance",
                    "symbol": "BTC/USDT",
                    "state": "RUNNING",
                    "last_event_age_ms": 25,
                    "paper_only": True,
                    "orders_submitted": False,
                    "execution_authorized": False,
                }

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            health = root / "top_of_book_health.json"
            output = root / "websocket_ticker_events.jsonl"
            backup = root / "websocket_ticker_events.jsonl.1"
            _write_health(
                health,
                status="RUNNING",
                collectors=[FakeCollector()],
                counters={
                    "events_written": 12,
                    "invalid_tickers_ignored": 1,
                    "write_errors": 0,
                    "collector_errors": 0,
                    "reconnects": 2,
                },
                symbols=["BTC/USDT"],
                venues=["binance"],
                output=output,
                backup=backup,
                max_bytes=1024,
            )

            report = json.loads(health.read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "RUNNING")
            self.assertEqual(report["collectors"][0]["state"], "RUNNING")
            self.assertEqual(report["counters"]["reconnects"], 2)
            self.assertTrue(report["paper_only"])
            self.assertFalse(report["orders_submitted"])
            self.assertFalse(report["execution_authorized"])
            self.assertFalse((root / "top_of_book_health.json.tmp").exists())


if __name__ == "__main__":
    unittest.main()
