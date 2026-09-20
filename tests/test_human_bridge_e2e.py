from pathlib import Path

from PC_ENGINE.browser.connector import BrowserTradingConnector


class FakeLocator:
    def __init__(self, values, key):
        self.values = values
        self.key = key

    @property
    def first(self):
        return self

    def fill(self, value):
        self.values[self.key] = value


class FakePage:
    def __init__(self):
        self.url = "https://example.test/form"
        self.values = {}

    def locator(self, selector):
        return FakeLocator(self.values, selector)


class FakeManager:
    def __init__(self):
        self.page_obj = FakePage()
        self.current_session = "session-a"

    def page(self, platform, url=None):
        return self.page_obj

    def session_id(self, platform):
        return self.current_session


def make_connector(tmp_path: Path):
    manager = FakeManager()
    config = {
        "enabled": True,
        "trading_url": "https://example.test/form",
        "human_bridge_data_dir": str(tmp_path / "bridge"),
        "human_interaction": {"enabled": True},
        "selectors": {"code_input": "#code"},
    }
    return BrowserTradingConnector("binance", config, manager)


def test_human_bridge_end_to_end_same_session(tmp_path):
    connector = make_connector(tmp_path)
    request = connector.human_bridge.create_request(
        "binance", "CUSTOM", "Input", "Human input",
        fields=[{"name": "code", "type": "text"}],
        session_id=connector.manager.session_id("binance"),
    )
    token = connector.human_bridge.claim_token(request.request_id)
    assert token
    assert connector.human_bridge.respond(
        request.request_id, action="fill", values={"code": "123456"}, claim_token=token
    )

    result = connector.resume_human_interaction(request.request_id)

    assert result["ok"] is True
    assert result["status"] == "completed"
    assert connector.manager.page_obj.values["#code"] == "123456"
    assert connector.human_bridge.get(request.request_id).status == "COMPLETED"
    assert connector.human_bridge.peek_response(request.request_id) is None


def test_human_bridge_rejects_replaced_session(tmp_path):
    connector = make_connector(tmp_path)
    request = connector.human_bridge.create_request(
        "binance", "CUSTOM", "Input", "Human input",
        session_id=connector.manager.session_id("binance"),
    )
    token = connector.human_bridge.claim_token(request.request_id)
    assert connector.human_bridge.respond(
        request.request_id, action="fill", values={"code": "654321"}, claim_token=token
    )

    connector.manager.current_session = "replacement-session"
    result = connector.resume_human_interaction(request.request_id)

    assert result["ok"] is False
    assert result["status"] == "session_mismatch"
    assert connector.human_bridge.get(request.request_id).status == "CANCELLED"
    assert connector.human_bridge.peek_response(request.request_id) is None
