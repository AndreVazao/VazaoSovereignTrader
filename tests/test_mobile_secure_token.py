from __future__ import annotations

from MOBILE_APP.secure_token import load_device_token, save_device_token


def test_secure_token_storage_never_falls_back_to_plaintext(tmp_path):
    path = tmp_path / "paired_device_token.bin"
    assert save_device_token(path, "device-token-secret") is False
    assert not path.exists()
    assert load_device_token(path) == ""
