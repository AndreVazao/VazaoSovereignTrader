from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .manager import BrowserManager
from PC_ENGINE.human_bridge.bridge import HumanInteractionBridge


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
        self.actions_path = Path(config.get("actions_log", f"PC_ENGINE/data/browser/{platform}_actions.jsonl"))
        self.actions_path.parent.mkdir(parents=True, exist_ok=True)
        self.human_bridge = HumanInteractionBridge(
            config.get("human_bridge_data_dir", "PC_ENGINE/data/human_bridge"),
            default_ttl_seconds=int(config.get("human_interaction_ttl_seconds", 900)),
        )

    def open(self) -> dict[str, Any]:
        if not self.enabled:
            raise RuntimeError(f"browser platform disabled: {self.platform}")
        url = str(self.config.get("trading_url") or self.config.get("login_url") or "")
        if not url:
            raise RuntimeError(f"missing trading_url/login_url for {self.platform}")
        page = self.manager.page(self.platform, url)
        interaction = self._detect_human_gate(page)
        if interaction:
            return {"ok": False, "status": "human_action_required", "request": interaction}
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
        interaction = self._detect_human_gate(page)
        if interaction:
            return self._finish(action_id, side, symbol, quantity, "human_action_required", f"human interaction request {interaction['request_id']}")
        try:
            self._fill_symbol(page, selectors, symbol)
            self._fill_quantity(page, selectors, quantity)
            button_key = "buy_button" if side == "buy" else "sell_button"
            button = self._locator(page, selectors.get(button_key))
            if not button:
                raise RuntimeError(f"missing selector: {button_key}")

            if not live:
                return self._finish(action_id, side, symbol, quantity, "paper", "browser dry-run: form prepared; submit not clicked")

            button.click()
            self._wait_for_confirmation(page, selectors)
            return self._finish(action_id, side, symbol, quantity, "submitted", "browser order submitted")
        except Exception as exc:
            self._capture(page, action_id)
            return self._finish(action_id, side, symbol, quantity, "error", str(exc))

    def resume_human_interaction(self, request_id: str) -> dict[str, Any]:
        request = self.human_bridge.get(request_id)
        if request is None:
            return {"ok": False, "status": "not_found"}
        if request.platform != self.platform:
            return {"ok": False, "status": "platform_mismatch"}
        if request.expires_at and time.time() >= request.expires_at:
            self.human_bridge.cancel(request_id)
            return {"ok": False, "status": "expired"}
        current_session = self.manager.session_id(self.platform)
        if request.session_id and request.session_id != current_session:
            self.human_bridge.cancel(request_id)
            return {"ok": False, "status": "session_mismatch"}
        if request.status != "RESPONDED":
            return {"ok": False, "status": "waiting" if request.status == "PENDING" else request.status.lower()}

        response = self.human_bridge.peek_response(request_id)
        if not response:
            return {"ok": False, "status": "response_missing"}

        page = self.manager.page(self.platform, self.config.get("trading_url"))
        action = response.get("action", "fill")
        values = response.get("values", {})
        selectors = self.config.get("selectors", {})
        try:
            if action == "click":
                page.mouse.click(float(values["x"]), float(values["y"]))
            elif action == "type":
                page.keyboard.type(str(values.get("text", "")))
            elif action == "press":
                page.keyboard.press(str(values.get("key", "Enter")))
            else:
                for name, value in values.items():
                    selector = selectors.get(f"{name}_input") or selectors.get(name)
                    if selector:
                        page.locator(str(selector)).first.fill(str(value))
            if not self.human_bridge.mark_applied(request_id):
                return {"ok": False, "status": "invalid_request_state"}
            self.human_bridge.consume_response(request_id)
            self.human_bridge.mark_completed(request_id)
            return {"ok": True, "status": "completed", "action": action}
        except Exception as exc:
            return {"ok": False, "status": "apply_error", "message": str(exc)}

    def _detect_human_gate(self, page: Any) -> dict[str, Any] | None:
        settings = self.config.get("human_interaction", {})
        if not bool(settings.get("enabled", True)):
            return None
        url = (page.url or "").lower()
        try:
            text = page.locator("body").inner_text(timeout=1000).lower()
        except Exception:
            text = ""
        captcha = any(x in text or x in url for x in ("captcha", "verify you are human", "robot check"))
        otp = any(x in text or x in url for x in ("two-factor", "2fa", "one-time password", "verification code", "security code"))
        login = any(x in url for x in ("/login", "/signin", "/sign-in", "/auth"))
        if not (captcha or otp or login):
            return None
        kind = "CAPTCHA" if captcha else ("OTP" if otp else "LOGIN")
        title = {"CAPTCHA": "CAPTCHA / verificação humana", "OTP": "Código de segurança / 2FA", "LOGIN": "Login necessário"}[kind]
        fields = settings.get("fields", [])
        if not fields:
            fields = (
                [{"name": "username", "type": "text", "label": "Utilizador"}, {"name": "password", "type": "secret", "label": "Password"}]
                if kind == "LOGIN"
                else ([{"name": "otp", "type": "secret", "label": "Código"}] if kind == "OTP" else [])
            )
        screenshot_dir = Path(self.config.get("evidence_dir", "PC_ENGINE/data/browser/evidence"))
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        path = screenshot_dir / f"{self.platform}_human_{int(time.time()*1000)}.png"
        try:
            page.screenshot(path=str(path), full_page=False)
        except Exception:
            path = None
        request = self.human_bridge.create_request(
            self.platform,
            kind,
            title,
            "O PC precisa de uma intervenção humana. Faz a operação no telefone e envia-a; o browser continua nesta sessão.",
            url=page.url,
            screenshot_path=str(path) if path else None,
            fields=fields,
            session_id=self.manager.session_id(self.platform),
        )
        return request.__dict__

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
            page.locator(selector).wait_for(state="visible", timeout=int(self.config.get("confirmation_timeout_ms", 10000)))
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
