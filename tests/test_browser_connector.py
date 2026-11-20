from __future__ import annotations

import pytest

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


@pytest.mark.parametrize("method_name", ["market_buy", "market_sell"])
def test_browser_live_cannot_be_enabled_by_local_configuration(tmp_path, method_name):
    actions_log = tmp_path / "actions.jsonl"
    connector = BrowserTradingConnector(
        "demo",
        {
            "enabled": True,
            "live_enabled": True,
            "require_confirmation": False,
            "confirmation_phrase": "CONFIRM",
            "actions_log": str(actions_log),
        },
        FakeManager(),
    )

    assert connector.live_enabled is False
    method = getattr(connector, method_name)
    with pytest.raises(PermissionError, match="PAPER-only"):
        method("BTC/USDT", 1.0, confirmation="CONFIRM", live=True)

    assert not actions_log.exists()
