from __future__ import annotations

from PC_ENGINE.api.server import create_app


class FakeEngine:
    mode = "PAPER"
    config = {"real_mode_guard": {"enabled": True}}

    def snapshot(self):
        return {"status": "OFF", "mode": self.mode}

    def run_preflight(self):
        return {"ok": True, "errors": [], "warnings": []}

    def start(self):
        return None

    def pause(self, _paused=True):
        return None

    def stop(self):
        return None

    def set_mode(self, mode):
        self.mode = mode


def test_health_is_public():
    client = create_app(FakeEngine(), token_env="VST_TEST_TOKEN").test_client()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["ok"] is True


def test_status_requires_token(monkeypatch):
    monkeypatch.setenv("VST_TEST_TOKEN", "secret-token")
    client = create_app(FakeEngine(), token_env="VST_TEST_TOKEN").test_client()

    assert client.get("/status").status_code == 401
    assert client.get("/status", headers={"X-Token": "secret-token"}).status_code == 200
