from __future__ import annotations

import json

import pytest

from PC_ENGINE.core.mobile_pairing import DEVICE_SCOPES, MobilePairingStore


def test_pairing_requires_explicit_approval_and_returns_token_once(tmp_path):
    store = MobilePairingStore(tmp_path, owner_id="andre")
    challenge = store.create_challenge("André Android")
    assert challenge["status"] == "PENDING"
    assert store.list_pending()[0]["device_name"] == "André Android"

    with pytest.raises(ValueError, match="challenge_not_approved"):
        store.complete(challenge["challenge_id"], challenge["confirmation_code"])
    with pytest.raises(PermissionError, match="confirmation_code_invalid"):
        store.approve(challenge["challenge_id"], "000000" if challenge["confirmation_code"] != "000000" else "000001")

    approved = store.approve(challenge["challenge_id"], challenge["confirmation_code"])
    assert approved["status"] == "APPROVED"
    result = store.complete(challenge["challenge_id"], challenge["confirmation_code"])
    token = result["device_token"]
    assert token
    assert result["scopes"] == sorted(DEVICE_SCOPES)
    assert "trade_real" not in result["scopes"]
    assert "manage_exchange_accounts" not in result["scopes"]

    persisted = json.loads((tmp_path / "mobile_pairing.json").read_text(encoding="utf-8"))
    assert token not in (tmp_path / "mobile_pairing.json").read_text(encoding="utf-8")
    assert persisted["devices"][result["device_id"]]["token_hash"]


def test_device_token_authenticates_and_revocation_invalidates_it(tmp_path):
    store = MobilePairingStore(tmp_path)
    challenge = store.create_challenge("Phone")
    store.approve(challenge["challenge_id"], challenge["confirmation_code"])
    result = store.complete(challenge["challenge_id"], challenge["confirmation_code"])

    principal = store.authenticate(result["device_token"])
    assert principal is not None
    assert principal.device_id == result["device_id"]
    assert principal.auth_method == "mobile_device_token"
    assert principal.has("trade_paper")
    assert not principal.has("trade_real")

    assert store.revoke(result["device_id"])["status"] == "REVOKED"
    assert store.authenticate(result["device_token"]) is None


def test_challenge_is_one_time_and_wrong_code_cannot_approve(tmp_path):
    store = MobilePairingStore(tmp_path)
    challenge = store.create_challenge("Phone")
    with pytest.raises(PermissionError):
        store.approve(challenge["challenge_id"], "999999")
    store.approve(challenge["challenge_id"], challenge["confirmation_code"])
    store.complete(challenge["challenge_id"], challenge["confirmation_code"])
    with pytest.raises(ValueError):
        store.complete(challenge["challenge_id"], challenge["confirmation_code"])


def test_device_name_is_required(tmp_path):
    store = MobilePairingStore(tmp_path)
    with pytest.raises(ValueError, match="device_name_required"):
        store.create_challenge("   ")

def test_challenge_expires_after_five_minutes(tmp_path, monkeypatch):
    import PC_ENGINE.core.mobile_pairing as pairing_module

    now = 1_800_000_000
    monkeypatch.setattr(pairing_module.time, "time", lambda: now)
    store = MobilePairingStore(tmp_path)
    challenge = store.create_challenge("Phone")
    monkeypatch.setattr(pairing_module.time, "time", lambda: now + 301)

    with pytest.raises(ValueError, match="challenge_not_pending_or_expired"):
        store.approve(challenge["challenge_id"], challenge["confirmation_code"])
