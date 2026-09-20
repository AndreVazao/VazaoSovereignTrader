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
    assert bridge.respond(item.request_id, action="fill", values={"password": "SUPER-SECRET"})
    raw = (tmp_path / "requests.jsonl").read_text(encoding="utf-8")
    assert "SUPER-SECRET" not in raw
    assert bridge.consume_response(item.request_id)["values"]["password"] == "SUPER-SECRET"
    assert bridge.consume_response(item.request_id) is None


def test_human_interaction_lifecycle(tmp_path):
    from PC_ENGINE.human_bridge.bridge import HumanInteractionBridge
    bridge = HumanInteractionBridge(str(tmp_path))
    item = bridge.create_request("binance", "OTP", "Codigo", "Introduz o codigo", fields=[{"name": "otp", "type": "secret"}])
    assert bridge.respond(item.request_id, action="fill", values={"otp": "123456"})
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
    assert bridge.respond(item.request_id, action="press", values={"key": "Enter"})
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
    assert bridge.respond(item.request_id, action="fill", values={"otp": "SECRET"})
    assert bridge.cancel(item.request_id)
    assert bridge.get(item.request_id).status == "CANCELLED"
    assert bridge.peek_response(item.request_id) is None
