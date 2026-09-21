from PC_ENGINE.core.identity import IdentityAuthenticator


def _env(values):
    return lambda key, default="": values.get(key, default)


def test_local_token_derives_owner_without_request_owner_id():
    config = {
        "owner": {"id": "andre"},
        "server": {"local_control_token_env": "VST_LOCAL_TOKEN"},
        "identity": {
            "owners": {
                "andre": {"user_id": "andre", "token_env": "ANDRE_TOKEN"}
            }
        },
    }
    auth = IdentityAuthenticator(config, _env({"ANDRE_TOKEN": "secret"}))
    principal = auth.authenticate("secret", device_id="andre-pc")
    assert principal.owner_id == "andre"
    assert principal.device_id == "andre-pc"
    assert principal.has("trade_real")


def test_second_owner_token_selects_only_that_owner():
    config = {
        "owner": {"id": "andre"},
        "server": {"local_control_token_env": "VST_LOCAL_TOKEN"},
        "identity": {
            "owners": {
                "andre": {"token_env": "ANDRE_TOKEN"},
                "genro": {"token_env": "GENRO_TOKEN"},
            }
        },
    }
    auth = IdentityAuthenticator(config, _env({"ANDRE_TOKEN": "a", "GENRO_TOKEN": "g"}))
    assert auth.authenticate("g").owner_id == "genro"


def test_owner_is_derived_from_credentials_not_request_data():
    config = {
        "owner": {"id": "andre"},
        "server": {"local_control_token_env": "VST_LOCAL_TOKEN"},
    }
    auth = IdentityAuthenticator(config, _env({"VST_LOCAL_TOKEN": "secret"}))
    assert auth.authenticate("secret").owner_id == "andre"


def test_tailscale_identity_can_be_required_and_bound_to_owner():
    config = {
        "owner": {"id": "genro"},
        "server": {"local_control_token_env": "VST_LOCAL_TOKEN"},
        "identity": {
            "require_device_identity": True,
            "owners": {
                "genro": {
                    "token_env": "GENRO_TOKEN",
                    "tailscale_identity": "genro-pc",
                }
            },
        },
    }
    auth = IdentityAuthenticator(config, _env({"GENRO_TOKEN": "secret"}))
    principal = auth.authenticate("secret", tailscale_identity="genro-pc")
    assert principal.owner_id == "genro"

    try:
        auth.authenticate("secret", tailscale_identity="andre-pc")
    except PermissionError as exc:
        assert "device_identity" in str(exc)
    else:
        raise AssertionError("cross-device identity must be rejected")


def test_scope_override_is_enforced():
    config = {
        "owner": {"id": "andre"},
        "server": {"local_control_token_env": "VST_LOCAL_TOKEN"},
        "identity": {
            "owners": {
                "andre": {"token_env": "ANDRE_TOKEN", "scopes": ["read_private_state"]}
            }
        },
    }
    auth = IdentityAuthenticator(config, _env({"ANDRE_TOKEN": "secret"}))
    principal = auth.authenticate("secret")
    assert principal.has("read_private_state")
    assert not principal.has("trade_real")
