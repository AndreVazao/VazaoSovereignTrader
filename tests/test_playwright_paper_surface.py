from __future__ import annotations

from PC_ENGINE.execution.playwright_paper_surface import (
    PlaywrightPaperConfig,
    PlaywrightPaperSurfaceAdapter,
)
from PC_ENGINE.execution.surface_adapters import ActionKind, Surface, SurfaceAction


def test_paper_buy_never_reports_exchange_order_reference() -> None:
    adapter = PlaywrightPaperSurfaceAdapter(
        PlaywrightPaperConfig(venue_id="demo", url="https://example.invalid")
    )

    feedback = adapter.execute(
        SurfaceAction(
            request_id="req-1",
            venue_id="demo",
            surface=Surface.WEB_BROWSER,
            action=ActionKind.BUY,
            paper_only=False,
        )
    )

    assert feedback.state == "PAPER_INTENT_RECORDED"
    assert feedback.acknowledged is True
    assert feedback.order_reference is None
    adapter.close()


def test_observe_can_use_an_existing_page_without_network_access() -> None:
    adapter = PlaywrightPaperSurfaceAdapter(
        PlaywrightPaperConfig(venue_id="demo", url="https://example.invalid")
    )

    class Page:
        url = "https://demo.invalid/trade"

        def title(self) -> str:
            return "Demo"

    adapter._page = Page()
    feedback = adapter.observe()

    assert feedback.state == "OBSERVED"
    assert "Demo" in feedback.detail
    adapter.close()


def test_browser_feedback_can_be_persisted_bounded(tmp_path) -> None:
    path = tmp_path / "surface-feedback.jsonl"
    adapter = PlaywrightPaperSurfaceAdapter(
        PlaywrightPaperConfig(
            venue_id="demo",
            url="https://example.invalid",
            feedback_path=str(path),
            feedback_max_records=2,
        )
    )

    class Page:
        url = "https://demo.invalid/trade"

        def title(self) -> str:
            return "Demo"

    adapter._page = Page()
    feedback = adapter.observe()

    assert feedback.state == "OBSERVED"
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert '"paper_only": true' in lines[0]
    assert '"execution_authorized": false' in lines[0]
    adapter.close()



def test_current_page_inventory_is_read_only_and_redacts_sensitive_labels() -> None:
    adapter = PlaywrightPaperSurfaceAdapter(
        PlaywrightPaperConfig(venue_id="demo", url="https://example.invalid")
    )

    class Page:
        url = "https://exchange.invalid/trade?account=12345678"

        def evaluate(self, _script):
            return {
                "headings": ["BTC/USDT trading", "Account 12345678"],
                "buttons": ["Buy", "Sell", "user@example.com"],
                "navigation": ["Spot", "Perpetual Futures"],
                "forms_count": 2,
                "visible_input_count": 3,
                "visible_input_types": {"text": 1, "password": 1, "number": 1},
            }

    adapter._page = Page()
    report = adapter.inspect_current_page()

    assert report["state"] == "INSPECTED"
    assert report["page_origin"] == "https://exchange.invalid"
    assert report["account_data_read"] is False
    assert report["input_values_read"] is False
    assert report["orders_submitted"] is False
    assert report["execution_authorized"] is False
    assert "12345678" not in str(report)
    assert "user@example.com" not in str(report)
    assert report["buttons"] == ["Buy", "Sell", "[redacted-email]"]
    assert report["forms_count"] == 2
    assert report["visible_input_types"]["password"] == 1
    adapter.close()


def test_current_page_inventory_reports_not_connected_without_open_page() -> None:
    adapter = PlaywrightPaperSurfaceAdapter(
        PlaywrightPaperConfig(venue_id="demo", url="https://example.invalid")
    )

    report = adapter.inspect_current_page()

    assert report["state"] == "NOT_CONNECTED"
    assert report["inspection"] == "CURRENT_PAGE_STRUCTURE_ONLY"
    assert report["account_data_read"] is False
    assert report["execution_authorized"] is False
    adapter.close()


def test_current_page_inventory_does_not_expose_page_url_path_or_query() -> None:
    adapter = PlaywrightPaperSurfaceAdapter(
        PlaywrightPaperConfig(venue_id="demo", url="https://example.invalid")
    )

    class Page:
        url = "https://exchange.invalid/user/private-account/12345678?token=secret"

        def evaluate(self, _script):
            return {"headings": [], "buttons": [], "navigation": [], "forms_count": 0,
                    "visible_input_count": 0, "visible_input_types": {}}

    adapter._page = Page()
    report = adapter.inspect_current_page()

    assert report["page_origin"] == "https://exchange.invalid"
    assert "private-account" not in str(report)
    assert "token=secret" not in str(report)
    adapter.close()
