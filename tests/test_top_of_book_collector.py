from __future__ import annotations

import json
import tempfile
import unittest
from types import SimpleNamespace
from pathlib import Path

from PC_ENGINE.tools.run_top_of_book_collector import (
    _append_bounded_line,
    _is_valid_top_of_book,
    _write_health,
)


class TopOfBookTickerValidationTests(unittest.TestCase):
    def test_rejects_non_numeric_bid_without_raising(self) -> None:
        event = SimpleNamespace(bid="not-a-price", ask="101", local_receive_wall_ns=1)
        self.assertFalse(_is_valid_top_of_book(event))

    def test_rejects_non_finite_and_invalid_market_values(self) -> None:
        cases = [
            (float("nan"), 101, 1),
            (100, float("inf"), 1),
            (0, 101, 1),
            (101, 100, 1),
            (100, 101, 0),
        ]
        for bid, ask, receive_wall_ns in cases:
            with self.subTest(bid=bid, ask=ask, receive_wall_ns=receive_wall_ns):
                self.assertFalse(_is_valid_top_of_book(SimpleNamespace(
                    bid=bid, ask=ask, local_receive_wall_ns=receive_wall_ns
                )))

    def test_accepts_valid_top_of_book(self) -> None:
        event = SimpleNamespace(bid="100.5", ask="101", local_receive_wall_ns="123")
        self.assertTrue(_is_valid_top_of_book(event))


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

    def test_oversized_record_is_dropped_without_growing_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "events.jsonl"
            backup = root / "events.jsonl.1"
            output.write_text("existing\n", encoding="utf-8")
            before = output.read_bytes()
            self.assertFalse(_append_bounded_line(output, backup, "x" * 32 + "\n", 16))
            self.assertEqual(output.read_bytes(), before)
            self.assertFalse(backup.exists())

    def test_rotation_keeps_each_file_within_cap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root / "events.jsonl"
            backup = root / "events.jsonl.1"
            cap = 10
            self.assertTrue(_append_bounded_line(output, backup, "1234\n", cap))
            self.assertTrue(_append_bounded_line(output, backup, "5678\n", cap))
            self.assertTrue(_append_bounded_line(output, backup, "abcd\n", cap))
            self.assertEqual(output.read_text(encoding="utf-8"), "abcd\n")
            self.assertEqual(backup.read_text(encoding="utf-8"), "1234\n5678\n")
            self.assertLessEqual(output.stat().st_size, cap)
            self.assertLessEqual(backup.stat().st_size, cap)


if __name__ == "__main__":
    unittest.main()
