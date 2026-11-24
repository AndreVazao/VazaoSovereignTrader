from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from PC_ENGINE.replay.synchronized_l2_research import analyze_book, build_report


def _row(**overrides):
    row = {
        "venue": "binance",
        "symbol": "BTC/USDT",
        "status": "SYNCED",
        "sequence": 10,
        "observation_time_ns": 1_000_000_000,
        "age_ms": 5.0,
        "bids": [
            {"price": 100.0, "quantity": 1.0},
            {"price": 99.0, "quantity": 2.0},
        ],
        "asks": [
            {"price": 101.0, "quantity": 0.5},
            {"price": 102.0, "quantity": 2.0},
        ],
        "analysis_eligible": True,
        "quality_status": "VALID",
        "paper_only": True,
        "orders_submitted": False,
        "execution_authorized": False,
    }
    row.update(overrides)
    return row


class SynchronizedL2ResearchTests(unittest.TestCase):
    def test_vwap_and_depth_impact_use_multiple_levels(self):
        sample = analyze_book(_row(), quote_notional=150.0)
        self.assertIsNotNone(sample)
        self.assertEqual(sample["buy"]["consumed_levels"], 2)
        self.assertEqual(sample["sell"]["consumed_levels"], 2)
        self.assertAlmostEqual(sample["buy"]["vwap"], (101.0 * 0.5 + 102.0 * (150.0 / 101.0 - 0.5)) / (150.0 / 101.0))
        self.assertGreater(sample["buy_impact_bps"], 0)
        self.assertGreater(sample["sell_impact_bps"], 0)

    def test_rejects_quality_flagged_and_non_paper_records(self):
        self.assertIsNone(analyze_book(_row(analysis_eligible=False, quality_status="FLAGGED")))
        self.assertIsNone(analyze_book(_row(orders_submitted=True)))
        self.assertIsNone(analyze_book(_row(execution_authorized=True)))

    def test_rejects_stale_crossed_unsorted_duplicate_and_zero_quantity(self):
        self.assertIsNone(analyze_book(_row(age_ms=1001.0)))
        self.assertIsNone(analyze_book(_row(asks=[{"price": 99.0, "quantity": 1.0}])))
        self.assertIsNone(analyze_book(_row(bids=[{"price": 99.0, "quantity": 1.0}, {"price": 100.0, "quantity": 1.0}])))
        self.assertIsNone(analyze_book(_row(bids=[{"price": 100.0, "quantity": 1.0}, {"price": 100.0, "quantity": 2.0}])))
        self.assertIsNone(analyze_book(_row(asks=[{"price": 101.0, "quantity": 0.0}])))

    def test_rejects_invalid_sequence_timestamp_and_depth_limit(self):
        self.assertIsNone(analyze_book(_row(sequence=True)))
        self.assertIsNone(analyze_book(_row(observation_time_ns=0)))
        self.assertIsNone(analyze_book(_row(bids=[{"price": 100.0, "quantity": 1.0}] * 3), max_levels_per_side=2))

    def test_fee_assumption_is_applied_per_side_without_claiming_edge(self):
        sample = analyze_book(_row(), quote_notional=50.0, fee_bps=7.5)
        self.assertAlmostEqual(sample["buy_cost_including_fee_bps"], sample["buy_impact_bps"] + 7.5)
        self.assertNotIn("net_edge_bps", sample)
        self.assertFalse(sample["execution_authorized"])

    def test_report_streams_files_and_bounds_sample_retention(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "binance_synchronized_orderbook_views.jsonl"
            rows = [_row(sequence=index + 1) for index in range(4)]
            lines = [json.dumps(rows[0]), json.dumps("not an object"), json.dumps(rows[1]),
                     json.dumps({"broken": True, "analysis_eligible": False, "quality_status": "FLAGGED"}),
                     json.dumps(rows[2]), json.dumps(rows[3]), "{broken"]
            path.write_bytes(("\n".join(lines) + "\n").encode("utf-8") + b"\xff\n")
            report = build_report(root, venues=("binance",), max_records=2)
        self.assertEqual(report["counters"]["valid_books_analyzed"], 4)
        self.assertEqual(report["counters"]["records_omitted_by_limit"], 2)
        self.assertEqual(report["counters"]["non_object_rows_ignored"], 1)
        self.assertEqual(report["counters"]["quality_flagged_ignored"], 1)
        self.assertEqual(report["counters"]["malformed_json_ignored"], 2)
        self.assertEqual(len(report["samples"]), 2)
        self.assertEqual(report["summaries"]["binance:BTC/USDT"]["samples"], 4)

    def test_report_reads_rotated_backup_before_active_and_preserves_sequence_continuity(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "binance_synchronized_orderbook_views.jsonl"
            backup = path.with_suffix(path.suffix + ".1")
            backup.write_text(
                "\\n".join(json.dumps(_row(sequence=value)) for value in (10, 11)) + "\\n",
                encoding="utf-8",
            )
            path.write_text(
                "\\n".join(json.dumps(_row(sequence=value)) for value in (12, 13)) + "\\n",
                encoding="utf-8",
            )
            report = build_report(root, venues=("binance",))
        self.assertEqual(report["counters"]["files_read"], 2)
        self.assertEqual(report["counters"]["backup_files_read"], 1)
        self.assertEqual(report["counters"]["valid_books_analyzed"], 4)
        self.assertEqual(report["counters"]["duplicate_or_out_of_order_sequences_ignored"], 0)
        self.assertEqual([row["sequence"] for row in report["samples"]], [10, 11, 12, 13])

    def test_report_rejects_sequence_repeats_across_rotated_segments(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "binance_synchronized_orderbook_views.jsonl"
            backup = path.with_suffix(path.suffix + ".1")
            backup.write_text(
                "\\n".join(json.dumps(_row(sequence=value)) for value in (10, 11)) + "\\n",
                encoding="utf-8",
            )
            path.write_text(
                "\\n".join(json.dumps(_row(sequence=value)) for value in (11, 12)) + "\\n",
                encoding="utf-8",
            )
            report = build_report(root, venues=("binance",))
        self.assertEqual(report["counters"]["valid_books_analyzed"], 3)
        self.assertEqual(report["counters"]["duplicate_or_out_of_order_sequences_ignored"], 1)

    def test_report_rejects_duplicate_or_out_of_order_sequences(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "binance_synchronized_orderbook_views.jsonl"
            rows = [_row(sequence=10), _row(sequence=10), _row(sequence=9), _row(sequence=11)]
            path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
            report = build_report(root, venues=("binance",))
        self.assertEqual(report["counters"]["valid_books_analyzed"], 2)
        self.assertEqual(report["counters"]["duplicate_or_out_of_order_sequences_ignored"], 2)

    def test_invalid_book_state_resets_sequence_baseline_for_rebootstrap(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "binance_synchronized_orderbook_views.jsonl"
            invalid = _row(sequence=11, status="INVALID", analysis_eligible=False, quality_status="FLAGGED")
            rows = [_row(sequence=10), invalid, _row(sequence=1)]
            path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
            report = build_report(root, venues=("binance",))
        self.assertEqual(report["counters"]["valid_books_analyzed"], 2)
        self.assertEqual(report["counters"]["duplicate_or_out_of_order_sequences_ignored"], 0)

    def test_missing_files_return_empty_report(self):
        with tempfile.TemporaryDirectory() as temp:
            report = build_report(temp)
        self.assertEqual(report["status"], "EMPTY")
        self.assertEqual(report["counters"]["files_missing"], 3)


if __name__ == "__main__":
    unittest.main()
