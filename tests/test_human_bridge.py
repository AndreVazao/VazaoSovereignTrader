from pathlib import Path
from PC_ENGINE.human_bridge.bridge import HumanInteractionBridge

def test_request_survives_new_bridge_instance(tmp_path: Path):
    first = HumanInteractionBridge(str(tmp_path))
    item = first.create_request("binance", "OTP", "Código de segurança", "Introduz o código recebido por SMS.", fields=[{"name": "otp", "type": "secret", "required": True}])
    second = HumanInteractionBridge(str(tmp_path))
    pending = second.pending()
    assert pending[0]["request_id"] == item.request_id
    assert pending[0]["status"] == "PENDING"

def test_secret_response_is_not_written_to_disk(tmp_path: Path):
    bridge = HumanInteractionBridge(str(tmp_path))
    item = bridge.create_request("x", "LOGIN", "Login", "Credenciais necessárias")
    assert bridge.respond(item.request_id, action="fill", values={"password": "SUPER-SECRET"}, claim_token=bridge.claim_token(item.request_id))
    raw = (tmp_path / "requests.jsonl").read_text(encoding="utf-8")
    assert "SUPER-SECRET" not in raw
    assert bridge.consume_response(item.request_id)["values"]["password"] == "SUPER-SECRET"
    assert bridge.consume_response(item.request_id) is None


def test_human_interaction_lifecycle(tmp_path):
    from PC_ENGINE.human_bridge.bridge import HumanInteractionBridge
    bridge = HumanInteractionBridge(str(tmp_path))
    item = bridge.create_request("binance", "OTP", "Codigo", "Introduz o codigo", fields=[{"name": "otp", "type": "secret"}])
    assert bridge.respond(item.request_id, action="fill", values={"otp": "123456"}, claim_token=bridge.claim_token(item.request_id))
    assert bridge.mark_applied(item.request_id)
    assert bridge.mark_completed(item.request_id)


def test_response_can_be_peeked_without_consuming(tmp_path):
    bridge = HumanInteractionBridge(str(tmp_path))
    item = bridge.create_request(
        "binance",
        "OTP",
        "Codigo",
        "Introduz o codigo",
        session_id="browser-session-1",
    )
    assert bridge.respond(item.request_id, action="press", values={"key": "Enter"}, claim_token=bridge.claim_token(item.request_id))
    first = bridge.peek_response(item.request_id)
    second = bridge.peek_response(item.request_id)
    assert first == second
    assert first["values"]["key"] == "Enter"
    assert bridge.consume_response(item.request_id)["action"] == "press"
    assert bridge.consume_response(item.request_id) is None


def test_session_binding_and_expiry_metadata(tmp_path):
    bridge = HumanInteractionBridge(str(tmp_path), default_ttl_seconds=60)
    item = bridge.create_request(
        "binance",
        "LOGIN",
        "Login",
        "Intervencao humana",
        session_id="session-a",
    )
    assert item.session_id == "session-a"
    assert item.expires_at > item.created_at
    assert bridge.respond(item.request_id, action="fill", values={"otp": "123456"})
    assert bridge.get(item.request_id).status == "RESPONDED"


def test_responded_request_can_be_cancelled_and_secret_removed(tmp_path):
    bridge = HumanInteractionBridge(str(tmp_path))
    item = bridge.create_request("binance", "OTP", "Codigo", "Intervencao")
    assert bridge.respond(item.request_id, action="fill", values={"otp": "SECRET"}, claim_token=bridge.claim_token(item.request_id))
    assert bridge.cancel(item.request_id)
    assert bridge.get(item.request_id).status == "CANCELLED"
    assert bridge.peek_response(item.request_id) is None


def test_response_requires_per_request_claim_token(tmp_path):
    bridge = HumanInteractionBridge(str(tmp_path))
    item = bridge.create_request("binance", "OTP", "Codigo", "Intervencao")
    assert not bridge.respond(item.request_id, action="fill", values={"otp": "123456"}, claim_token="wrong")
    token = bridge.claim_token(item.request_id)
    assert token
    assert bridge.respond(item.request_id, action="fill", values={"otp": "123456"}, claim_token=token)


def test_claim_token_is_not_persisted(tmp_path):
    bridge = HumanInteractionBridge(str(tmp_path))
    bridge.create_request("binance", "OTP", "Codigo", "Intervencao")
    item = bridge.get(bridge.pending()[0]["request_id"])
    token = bridge.claim_token(item.request_id)
    raw = (tmp_path / "requests.jsonl").read_text(encoding="utf-8")
    assert token not in raw
    assert item.claim_token_hash in raw


def test_expired_request_is_transitioned_and_cannot_be_replayed(tmp_path):
    import time
    bridge = HumanInteractionBridge(str(tmp_path), default_ttl_seconds=30)
    item = bridge.create_request("binance", "OTP", "Codigo", "Intervencao")
    item.expires_at = time.time() - 1
    bridge._append(item)
    assert bridge.pending() == []
    assert bridge.get(item.request_id).status == "EXPIRED"
    assert not bridge.respond(item.request_id, action="fill", values={"otp": "123456"}, claim_token=bridge.claim_token(item.request_id) or "")


def test_claim_can_be_reissued_after_process_recovery(tmp_path):
    bridge = HumanInteractionBridge(str(tmp_path))
    item = bridge.create_request("binance", "OTP", "Codigo", "Intervencao")
    old_token = bridge.claim_token(item.request_id)
    bridge._RAM_CLAIMS.pop(item.request_id, None)
    new_token = bridge.reissue_claim(item.request_id)
    assert new_token and new_token != old_token
    assert not bridge.respond(item.request_id, action="fill", values={"otp": "1"}, claim_token=old_token or "")
    assert bridge.respond(item.request_id, action="fill", values={"otp": "2"}, claim_token=new_token)


def test_watchdog_heartbeat_and_stale_detection(tmp_path):
    from PC_ENGINE.human_bridge.watchdog import HumanBridgeWatchdog
    bridge = HumanInteractionBridge(str(tmp_path))
    watchdog = HumanBridgeWatchdog(bridge, {"mobile_timeout_seconds": 10, "pc_timeout_seconds": 10})
    watchdog.heartbeat("mobile")
    watchdog.heartbeat("pc")
    fresh = watchdog.check(time.time())
    assert fresh["ok"] is True
    stale = watchdog.check(time.time() + 11)
    assert stale["safe_state"] is True
    assert stale["mobile"]["stale"] is True
    assert stale["pc"]["stale"] is True


def test_watchdog_cancels_stuck_response(tmp_path):
    from PC_ENGINE.human_bridge.watchdog import HumanBridgeWatchdog
    bridge = HumanInteractionBridge(str(tmp_path))
    watchdog = HumanBridgeWatchdog(bridge, {"responded_timeout_seconds": 30})
    item = bridge.create_request("binance", "OTP", "Codigo", "Intervencao")
    assert bridge.respond(item.request_id, action="fill", values={"otp": "SECRET"}, claim_token=bridge.claim_token(item.request_id))
    current = bridge.get(item.request_id)
    current.updated_at = time.time() - 31
    bridge._append(current)
    result = watchdog.check(time.time())
    assert result["cancelled_stuck_responses"] == 1
    assert bridge.get(item.request_id).status == "CANCELLED"
    assert bridge.peek_response(item.request_id) is None
