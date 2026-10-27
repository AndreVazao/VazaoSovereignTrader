from PC_ENGINE.main import _server_host


def test_server_host_defaults_to_loopback_when_missing():
    assert _server_host({}) == "127.0.0.1"
    assert _server_host({"server": {}}) == "127.0.0.1"


def test_server_host_blank_value_fails_to_safe_loopback():
    assert _server_host({"server": {"host": "  "}}) == "127.0.0.1"


def test_server_host_explicit_override_is_preserved():
    assert _server_host({"server": {"host": "100.64.0.10"}}) == "100.64.0.10"

def test_server_host_rejects_wildcard_bind_addresses():
    assert _server_host({"server": {"host": "0.0.0.0"}}) == "127.0.0.1"
    assert _server_host({"server": {"host": "::"}}) == "127.0.0.1"
    assert _server_host({"server": {"host": "[::]"}}) == "127.0.0.1"
