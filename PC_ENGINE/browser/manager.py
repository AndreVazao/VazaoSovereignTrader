from __future__ import annotations

import threading
import uuid
from pathlib import Path
from typing import Any

from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright


class BrowserManager:
    """Persistent Chromium profiles, one isolated context per platform.

    A fresh in-memory session id is created whenever a platform page is created.
    Human-bridge requests are bound to that id so a stale response cannot be
    applied to a different browser page after a restart/replacement.
    """

    def __init__(self, settings: dict[str, Any] | None = None):
        self.settings = settings or {}
        self.root = Path(self.settings.get("profile_dir", "PC_ENGINE/data/browser/profiles"))
        self.root.mkdir(parents=True, exist_ok=True)
        self.headless = bool(self.settings.get("headless", False))
        self.timeout_ms = int(self.settings.get("timeout_ms", 15000))
        self._playwright = None
        self._browser: Browser | None = None
        self._contexts: dict[str, BrowserContext] = {}
        self._pages: dict[str, Page] = {}
        self._session_ids: dict[str, str] = {}
        self._lock = threading.RLock()

    def start(self) -> None:
        with self._lock:
            if self._playwright is not None:
                return
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=self.headless)

    def stop(self) -> None:
        with self._lock:
            for context in list(self._contexts.values()):
                try:
                    context.close()
                except Exception:
                    pass
            self._contexts.clear()
            self._pages.clear()
            self._session_ids.clear()
            if self._browser is not None:
                try:
                    self._browser.close()
                except Exception:
                    pass
            self._browser = None
            if self._playwright is not None:
                try:
                    self._playwright.stop()
                except Exception:
                    pass
            self._playwright = None

    def page(self, platform: str, url: str | None = None) -> Page:
        self.start()
        key = self._safe_key(platform)
        with self._lock:
            page = self._pages.get(key)
            if page is not None and not page.is_closed():
                if url and page.url == "about:blank":
                    page.goto(url, wait_until="domcontentloaded", timeout=self.timeout_ms)
                return page

            profile = self.root / key
            profile.mkdir(parents=True, exist_ok=True)
            context = self._contexts.get(key)
            if context is None:
                if self._playwright is None:
                    raise RuntimeError("browser runtime is not started")
                context = self._playwright.chromium.launch_persistent_context(
                    user_data_dir=str(profile),
                    headless=self.headless,
                    viewport={"width": 1440, "height": 1000},
                )
                self._contexts[key] = context

            page = context.pages[0] if context.pages else context.new_page()
            page.set_default_timeout(self.timeout_ms)
            self._pages[key] = page
            self._session_ids[key] = uuid.uuid4().hex
            if url and (page.url == "about:blank" or page.url != url):
                page.goto(url, wait_until="domcontentloaded", timeout=self.timeout_ms)
            return page

    def session_id(self, platform: str) -> str:
        key = self._safe_key(platform)
        with self._lock:
            if key not in self._session_ids:
                self.page(platform)
            return self._session_ids[key]

    def close_platform(self, platform: str) -> None:
        key = self._safe_key(platform)
        with self._lock:
            page = self._pages.pop(key, None)
            self._session_ids.pop(key, None)
            if page is not None:
                try:
                    page.close()
                except Exception:
                    pass
            context = self._contexts.pop(key, None)
            if context is not None:
                try:
                    context.close()
                except Exception:
                    pass

    @staticmethod
    def _safe_key(value: str) -> str:
        cleaned = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in value.strip())
        return cleaned[:80] or "platform"

    def __enter__(self) -> "BrowserManager":
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.stop()
