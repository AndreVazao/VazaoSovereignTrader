from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent


class MobileStartupContractTests(unittest.TestCase):
    def test_mobile_python_sources_parse(self) -> None:
        for path in ROOT.rglob("*.py"):
            with self.subTest(path=str(path.relative_to(ROOT))):
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    def test_status_model_widget_is_not_reparented_between_pages(self) -> None:
        source = (ROOT / "ui.py").read_text(encoding="utf-8")
        self.assertNotIn("bar.add_widget(app.status)", source)
        self.assertIn("app.status.bind(text=", source)
        self.assertIn("app._chat_scroll = scroll", source)

    def test_startup_failure_has_local_diagnostic_fallback(self) -> None:
        source = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn("return self._startup_error_view(type(exc).__name__)", source)
        self.assertIn('"startup_error.log"', source)
        self.assertIn("traceback.format_tb", source)
        self.assertNotIn('self._request("POST", "/startup-error"', source)


if __name__ == "__main__":
    unittest.main()
