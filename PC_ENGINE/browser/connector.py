from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .manager import BrowserManager


@dataclass
class BrowserAction:
    action_id: str
    platform: str
    action: str
    symbol: str | None
    side: str | None
    quantity: float | None
    status: str
    message: str
    timestamp: float


class BrowserTradingConnector:
    """Generic browser execution connector.

    Platform-specific selectors remain in local configuration.
    Live browser orders are disabled unless explicitly enabled.
    """

    def __init__(self, platform: str, config: dict[str, Any], manager: BrowserManager):
        self.platform = platform
        self.config = config
        self.manager = manager
        self.enabled = bool(config.get("enabled", False))
        self.live_enabled = bool(config.get("live_enabled", False))
        self.require_confirmation = bool(config.get("require_confirmation", True))
        self.confirmation_phrase = str(config.get("confirmation_phrase", "EXECUTE WEB ORDER"))
        self.actions_path = Path(config.get(
            "actions_log",
            f"PC_ENGINE/data/browser/{platform}_actions.jsonl",
        ))
        self.actions_path.parent.mkdir(parents=True, exist_ok=True)

    def open(self) -> dict[str, Any]:
        if not self.enabled:
            raise RuntimeError(f"browser platform disabled: {self.platform}")
        url = str(self.config.get("trading_url") or self.config.get("login_url") or "")
        if not url:
            raise RuntimeError(f"missing trading_url/login_url for {self.platform}")
        page = self.manager.page(self.platform, url)
        return {"ok": True, "url": page.url, "title": page.title()}

    def market_buy(self, symbol: str, quantity: float, *, confirmation: str = "", live: bool = False) -> dict[str, Any]:
        return self._place_order("buy", symbol, quantity, confirmation=confirmation, live=live)

    def market_sell(self, symbol: str, quantity: float, *, confirmation: str = "", live: bool = False) -> dict[str, Any]:
        return self._place_order("sell", symbol, quantity, confirmation=confirmation, live=live)

    def _place_order(self, side: str, symbol: str, quantity: float, *, confirmation: str, live: bool) -> dict[str, Any]:
        action_id = uuid.uuid4().hex
        self._require_live_authorization(live, confirmation)
        if quantity <= 0:
            return self._finish(action_id, side, symbol, quantity, "rejected", "quantity must be positive")

        page = self.manager.page(self.platform, self.config.get("trading_url"))
        selectors = self.config.get("selectors", {})
        try:
            self._fill_symbol(page, selectors, symbol)
            self._fill_quantity(page, selectors, quantity)
            button_key = "buy_button" if side == "buy" else "sell_button"
            button = self._locator(page, selectors.get(button_key))
            if not button:
                raise RuntimeError(f"missing selector: {button_key}")

            if not live:
                return self._finish(action_id, side, symbol, quantity, "paper",
                    "browser dry-run: form prepared; submit not clicked")

            button.click()
            self._wait_for_confirmation(page, selectors)
            return self._finish(action_id, side, symbol, quantity, "submitted",
                "browser order submitted")
        except Exception as exc:
            self._capture(page, action_id)
            return self._finish(action_id, side, symbol, quantity, "error", str(exc))

    def _require_live_authorization(self, live: bool, confirmation: str) -> None:
        if not live:
            return
        if not self.enabled or not self.live_enabled:
            raise PermissionError("live browser trading is disabled")
        if self.require_confirmation and confirmation != self.confirmation_phrase:
            raise PermissionError("invalid browser order confirmation")

    def _fill_symbol(self, page: Any, selectors: dict[str, Any], symbol: str) -> None:
        selector = selectors.get("symbol_input")
        if not selector:
            return
        locator = self._locator(page, selector)
        if not locator:
            raise RuntimeError("missing selector: symbol_input")
        locator.fill(symbol)
        page.wait_for_timeout(int(self.config.get("settle_ms", 250)))

    def _fill_quantity(self, page: Any, selectors: dict[str, Any], quantity: float) -> None:
        selector = selectors.get("quantity_input")
        if not selector:
            raise RuntimeError("missing selector: quantity_input")
        locator = self._locator(page, selector)
        if not locator:
            raise RuntimeError("missing selector: quantity_input")
        locator.fill(self._number(quantity))

    def _wait_for_confirmation(self, page: Any, selectors: dict[str, Any]) -> None:
        selector = selectors.get("order_confirmation")
        if selector:
            page.locator(selector).wait_for(state="visible",
                timeout=int(self.config.get("confirmation_timeout_ms", 10000)))
        else:
            page.wait_for_timeout(int(self.config.get("post_submit_wait_ms", 1000)))

    @staticmethod
    def _locator(page: Any, selector: Any):
        if not selector:
            return None
        return page.locator(str(selector)).first

    def _capture(self, page: Any, action_id: str) -> None:
        try:
            path = Path(self.config.get("evidence_dir", "PC_ENGINE/data/browser/evidence"))
            path.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(path / f"{self.platform}_{action_id}.png"), full_page=True)
        except Exception:
            pass

    def _finish(self, action_id: str, side: str, symbol: str, quantity: float, status: str, message: str) -> dict[str, Any]:
        row = BrowserAction(action_id, self.platform, "market_order", symbol, side, quantity, status, message, time.time())
        with self.actions_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(row), ensure_ascii=False) + "\n")
        return asdict(row)

    @staticmethod
    def _number(value: float) -> str:
        return f"{float(value):.12f}".rstrip("0").rstrip(".")
