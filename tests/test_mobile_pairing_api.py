from __future__ import annotations

from PC_ENGINE.api.server import create_app
from PC_ENGINE.core.mobile_pairing import MobilePairingStore


class FakeOwnerContext:
    def snapshot(self):
        return {"owner_id": "andre"}


class FakeEngine:
    owner_id = "andre"
    owner_context = FakeOwnerContext()
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


def test_pairing_routes_issue_restricted_revocable_device_token(tmp_path, monkeypatch):
    monkeypatch.setenv("VST_TEST_TOKEN", "owner-secret")
    engine = FakeEngine()
    engine.config = {
        "real_mode_guard": {"enabled": True},
        "mobile_pairing": {"data_dir": str(tmp_path / "pairing")},
    }
    client = create_app(engine, token_env="VST_TEST_TOKEN").test_client()
    owner_headers = {"X-Token": "owner-secret"}

    denied = client.post("/mobile-pairing/request", json={"device_name": "Phone"})
    assert denied.status_code == 401

    request_response = client.post(
        "/mobile-pairing/request",
        headers=owner_headers,
        json={"device_name": "Test Android"},
    )
    assert request_response.status_code == 200
    challenge = request_response.get_json()
    assert challenge["status"] == "PENDING"

    store = MobilePairingStore(tmp_path / "pairing", owner_id="andre")
    store.approve(challenge["challenge_id"], challenge["confirmation_code"])
    status = client.get(
        f"/mobile-pairing/status/{challenge['challenge_id']}",
        headers=owner_headers,
    )
    assert status.status_code == 200
    assert status.get_json()["status"] == "APPROVED"

    completed = client.post(
        "/mobile-pairing/complete",
        headers=owner_headers,
        json={
            "challenge_id": challenge["challenge_id"],
            "confirmation_code": challenge["confirmation_code"],
        },
    )
    assert completed.status_code == 200
    device = completed.get_json()
    device_headers = {"X-Token": device["device_token"]}

    identity = client.get("/identity", headers=device_headers)
    assert identity.status_code == 200
    principal = identity.get_json()["principal"]
    assert principal["device_id"] == device["device_id"]
    assert "trade_paper" in principal["scopes"]
    assert "trade_real" not in principal["scopes"]
    assert "manage_exchange_accounts" not in principal["scopes"]

    real_arm = client.post("/real/arm", headers=device_headers, json={"phrase": "EU ACEITO O RISCO"})
    assert real_arm.status_code == 401

    revoke = client.post(
        "/mobile-pairing/revoke",
        headers=owner_headers,
        json={"device_id": device["device_id"]},
    )
    assert revoke.status_code == 200
    assert client.get("/identity", headers=device_headers).status_code == 401


def test_pairing_routes_do_not_allow_device_token_to_manage_devices(tmp_path, monkeypatch):
    monkeypatch.setenv("VST_TEST_TOKEN", "owner-secret")
    engine = FakeEngine()
    engine.config = {
        "real_mode_guard": {"enabled": True},
        "mobile_pairing": {"data_dir": str(tmp_path / "pairing")},
    }
    client = create_app(engine, token_env="VST_TEST_TOKEN").test_client()
    store = MobilePairingStore(tmp_path / "pairing", owner_id="andre")
    challenge = store.create_challenge("Phone")
    store.approve(challenge["challenge_id"], challenge["confirmation_code"])
    result = store.complete(challenge["challenge_id"], challenge["confirmation_code"])

    response = client.get("/mobile-pairing/devices", headers={"X-Token": result["device_token"]})
    assert response.status_code == 403
