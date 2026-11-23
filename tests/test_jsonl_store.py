from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PC_ENGINE.market_events.jsonl_store import append_bounded_jsonl


class BoundedJsonlStoreTests(unittest.TestCase):
    def test_append_and_rotate_with_exact_byte_cap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "events.jsonl"
            backup = Path(tmp) / "events.jsonl.1"
            self.assertTrue(append_bounded_jsonl(output, backup, "1234\n", 10))
            self.assertTrue(append_bounded_jsonl(output, backup, "5678\n", 10))
            self.assertTrue(append_bounded_jsonl(output, backup, "abcd\n", 10))
            self.assertEqual(output.read_text(encoding="utf-8"), "abcd\n")
            self.assertEqual(backup.read_text(encoding="utf-8"), "1234\n5678\n")
            self.assertLessEqual(output.stat().st_size, 10)
            self.assertLessEqual(backup.stat().st_size, 10)

    def test_oversized_record_does_not_mutate_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "events.jsonl"
            backup = Path(tmp) / "events.jsonl.1"
            output.write_text("existing\n", encoding="utf-8")
            before = output.read_bytes()
            self.assertFalse(append_bounded_jsonl(output, backup, "x" * 20 + "\n", 10))
            self.assertEqual(output.read_bytes(), before)
            self.assertFalse(backup.exists())

    def test_rejects_invalid_record_and_cap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "events.jsonl"
            backup = Path(tmp) / "events.jsonl.1"
            with self.assertRaisesRegex(ValueError, "newline"):
                append_bounded_jsonl(output, backup, "not-jsonl", 100)
            with self.assertRaisesRegex(ValueError, "positive"):
                append_bounded_jsonl(output, backup, "{}\n", 0)

    def test_rejects_symlink_targets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            real = root / "real.jsonl"
            link = root / "linked.jsonl"
            real.write_text("safe\n", encoding="utf-8")
            try:
                link.symlink_to(real)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable in this environment")
            with self.assertRaisesRegex(OSError, "symlink"):
                append_bounded_jsonl(link, root / "backup.jsonl", "{}\n", 100)
            self.assertEqual(real.read_text(encoding="utf-8"), "safe\n")


if __name__ == "__main__":
    unittest.main()
