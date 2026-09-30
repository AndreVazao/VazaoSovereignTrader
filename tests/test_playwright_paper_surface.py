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
