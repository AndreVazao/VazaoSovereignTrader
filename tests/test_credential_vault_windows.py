from __future__ import annotations

import json
import sys

import pytest

from PC_ENGINE.core.credential_vault import WindowsCredentialVault


@pytest.mark.skipif(sys.platform != "win32", reason="native DPAPI is available only on Windows")
def test_native_windows_dpapi_current_user_round_trip(tmp_path):
    credentials = {
        "api_key": "vst-native-dpapi-test-key",
        "api_secret": "vst-native-dpapi-test-secret",
    }
    store = WindowsCredentialVault(tmp_path)

    metadata = store.save("binance", credentials)
    encrypted_path, metadata_path = store._paths("binance")
    encrypted = encrypted_path.read_bytes()
    metadata_text = metadata_path.read_text(encoding="utf-8")

    assert encrypted
    assert credentials["api_key"].encode() not in encrypted
    assert credentials["api_secret"].encode() not in encrypted
    assert credentials["api_key"] not in metadata_text
    assert credentials["api_secret"] not in metadata_text
    assert metadata["venue"] == "binance"
    assert store.load("binance") == credentials
    assert store.metadata("binance")["configured"] is True

    store.delete("binance")
    assert store.metadata("binance") is None
    with pytest.raises(FileNotFoundError):
        store.load("binance")
