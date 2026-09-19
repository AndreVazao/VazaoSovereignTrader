from __future__ import annotations

from PC_ENGINE.browser.connector import BrowserTradingConnector


class FakeManager:
    def page(self, *_args, **_kwargs):
        raise RuntimeError("browser not started")


def test_browser_live_is_disabled_by_default(tmp_path):
    connector = BrowserTradingConnector(
        "demo",
        {"enabled": True, "actions_log": str(tmp_path / "actions.jsonl")},
        FakeManager(),
    )
    assert connector.enabled is True
    assert connector.live_enabled is False
    assert connector.require_confirmation is True


def test_browser_live_requires_explicit_enablement():
    connector = BrowserTradingConnector(
        "demo",
        {"enabled": True, "live_enabled": False, "confirmation_phrase": "CONFIRM"},
        FakeManager(),
    )
    try:
        connector._require_live_authorization(True, "CONFIRM")
    except PermissionError:
        return
    raise AssertionError("live browser trading must be disabled by default")
