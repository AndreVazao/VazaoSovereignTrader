from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

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
    feedback_path: str | None = None
    feedback_max_records: int = 2_000


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
        self._feedback_store = None
        if config.feedback_path:
            from .surface_feedback_store import ExecutionSurfaceFeedbackStore
            self._feedback_store = ExecutionSurfaceFeedbackStore(config.feedback_path, max_records=config.feedback_max_records)

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
        if self._feedback_store is not None:
            self._feedback_store.append(feedback)
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


    @staticmethod
    def _safe_inventory_label(value: Any) -> str:
        """Bound UI labels and redact common account-identifying patterns."""
        label = re.sub(r"\b[^\s@]+@[^\s@]+\.[^\s@]+\b", "[redacted-email]", str(value or ""))
        label = re.sub(r"\b\d{4,}\b", "[redacted-number]", label)
        return " ".join(label.split())[:100]

    def inspect_current_page(self) -> dict[str, Any]:
        """Return a bounded, read-only structural inventory of the current page.

        This deliberately does not read input values, cookies, storage, balances,
        positions, credentials, or execute clicks. It inspects only visible UI
        labels and aggregate form/input metadata on the current page.
        """
        base = {
            "venue_id": self.config.venue_id,
            "surface": self.surface.value,
            "inspection": "CURRENT_PAGE_STRUCTURE_ONLY",
            "paper_only": True,
            "orders_submitted": False,
            "execution_authorized": False,
            "account_data_read": False,
            "input_values_read": False,
        }
        if self._page is None:
            return {**base, "state": "NOT_CONNECTED", "detail": "No browser page is currently open."}
        try:
            raw = self._page.evaluate("""() => {
              const visible = (el) => !!(el && el.getClientRects && el.getClientRects().length);
              const label = (el) => (el.innerText || el.getAttribute('aria-label') || el.getAttribute('title') || '').trim();
              const collect = (selector, limit) => Array.from(document.querySelectorAll(selector))
                .filter(visible).map(label).filter(Boolean).slice(0, limit);
              const inputs = Array.from(document.querySelectorAll('input,textarea,select')).filter(visible);
              const inputTypes = {};
              for (const el of inputs) {
                const type = (el.tagName === 'INPUT' ? (el.getAttribute('type') || 'text') : el.tagName.toLowerCase()).toLowerCase();
                inputTypes[type] = (inputTypes[type] || 0) + 1;
              }
              return {
                headings: collect('h1,h2,h3,[role="heading"]', 30),
                buttons: collect('button,[role="button"]', 40),
                navigation: collect('nav a,[role="navigation"] a', 40),
                forms_count: document.forms.length,
                visible_input_count: inputs.length,
                visible_input_types: inputTypes
              };
            }""")
            split = urlsplit(str(getattr(self._page, "url", "")))
            origin = f"{split.scheme}://{split.netloc}" if split.scheme and split.netloc else None
            return {
                **base,
                "state": "INSPECTED",
                "page_origin": origin,
                "headings": [self._safe_inventory_label(v) for v in raw.get("headings", [])[:30]],
                "buttons": [self._safe_inventory_label(v) for v in raw.get("buttons", [])[:40]],
                "navigation": [self._safe_inventory_label(v) for v in raw.get("navigation", [])[:40]],
                "forms_count": max(0, int(raw.get("forms_count", 0))),
                "visible_input_count": max(0, int(raw.get("visible_input_count", 0))),
                "visible_input_types": {str(k)[:30]: max(0, int(v)) for k, v in list(raw.get("visible_input_types", {}).items())[:20]},
                "detail": "Structure only; balance, assets, positions, permissions and trading capabilities remain UNKNOWN until independently verified."
            }
        except Exception as exc:
            return {**base, "state": "INSPECTION_FAILED", "detail": f"{type(exc).__name__}: page structure could not be inspected."}

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
