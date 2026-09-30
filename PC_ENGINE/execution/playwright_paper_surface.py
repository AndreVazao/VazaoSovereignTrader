from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from .surface_adapters import (
    ActionKind,
    ExecutionSurfaceAdapter,
    Surface,
    SurfaceAction,
    SurfaceFeedback,
    paper_action,
    validate_feedback,
)

try:
    from playwright.sync_api import Browser, BrowserContext, Playwright, sync_playwright
except ImportError:
    Browser = Any
    BrowserContext = Any
    Playwright = Any
    sync_playwright = None


@dataclass(frozen=True)
class PlaywrightPaperConfig:
    venue_id: str
    url: str
    profile_dir: str | None = None
    headless: bool = True
    timeout_ms: int = 10_000


class PlaywrightPaperSurfaceAdapter(ExecutionSurfaceAdapter):
    """Concrete browser transport for observation and PAPER intent recording.

    The adapter can navigate and inspect a configured browser surface. It never
    clicks order controls, submits forms, invokes private APIs, or reports a
    PAPER intent as an exchange fill.
    """

    surface = Surface.WEB_BROWSER

    def __init__(self, config: PlaywrightPaperConfig) -> None:
        if not config.venue_id.strip():
            raise ValueError("venue_id is required")
        if not config.url.strip():
            raise ValueError("url is required")
        self.config = config
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Any = None

    @staticmethod
    def _now_ms() -> int:
        return int(time.time() * 1000)

    def _feedback(self, request_id: str, *, state: str, acknowledged: bool, detail: str = "") -> SurfaceFeedback:
        feedback = SurfaceFeedback(
            request_id=request_id,
            surface=self.surface,
            venue_id=self.config.venue_id,
            state=state,
            acknowledged=acknowledged,
            observed_at_ms=self._now_ms(),
            detail=detail,
            order_reference=None,
        )
        validate_feedback(feedback)
        return feedback

    def _ensure_page(self) -> Any:
        if sync_playwright is None:
            raise RuntimeError("Playwright is not installed")
        if self._page is not None:
            return self._page

        self._playwright = sync_playwright().start()
        if self.config.profile_dir:
            self._context = self._playwright.chromium.launch_persistent_context(
                self.config.profile_dir,
                headless=self.config.headless,
            )
        else:
            self._browser = self._playwright.chromium.launch(headless=self.config.headless)
            self._context = self._browser.new_context()

        self._page = self._context.new_page()
        self._page.set_default_timeout(self.config.timeout_ms)
        return self._page

    def probe(self) -> SurfaceFeedback:
        request_id = f"browser-probe-{self._now_ms()}"
        try:
            page = self._ensure_page()
            page.goto(self.config.url, wait_until="domcontentloaded")
            return self._feedback(
                request_id,
                state="CONNECTED",
                acknowledged=True,
                detail=f"url={page.url}; title={page.title()}",
            )
        except Exception as exc:
            return self._feedback(
                request_id,
                state="DOWN",
                acknowledged=False,
                detail=f"{type(exc).__name__}: {exc}",
            )

    def observe(self) -> SurfaceFeedback:
        request_id = f"browser-observe-{self._now_ms()}"
        try:
            page = self._ensure_page()
            return self._feedback(
                request_id,
                state="OBSERVED",
                acknowledged=True,
                detail=f"url={page.url}; title={page.title()}",
            )
        except Exception as exc:
            return self._feedback(
                request_id,
                state="DOWN",
                acknowledged=False,
                detail=f"{type(exc).__name__}: {exc}",
            )

    def execute(self, action: SurfaceAction) -> SurfaceFeedback:
        action = paper_action(action)
        if action.surface is not self.surface:
            raise ValueError("action surface does not match browser adapter")
        if action.action is ActionKind.CONNECT:
            return self.probe()
        if action.action is ActionKind.OBSERVE:
            return self.observe()
        return self._feedback(
            action.request_id,
            state="PAPER_INTENT_RECORDED",
            acknowledged=True,
            detail=f"action={action.action.value}; no browser order interaction performed",
        )

    def close(self) -> None:
        if self._context is not None:
            self._context.close()
        if self._browser is not None:
            self._browser.close()
        if self._playwright is not None:
            self._playwright.stop()
        self._page = None
        self._context = None
        self._browser = None
        self._playwright = None
