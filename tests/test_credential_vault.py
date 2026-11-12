from __future__ import annotations

import json
import sys

import pytest

from PC_ENGINE.core import credential_vault as vault


def _fake_dpapi(monkeypatch):
    monkeypatch.setattr(vault, "_dpapi_protect", lambda data: b"ENCRYPTED:" + data[::-1])
    monkeypatch.setattr(
        vault, "_dpapi_unprotect",
        lambda data: data[len(b"ENCRYPTED:"):][::-1] if data.startswith(b"ENCRYPTED:") else (_ for _ in ()).throw(ValueError("bad blob")),
    )


def test_unsupported_platform_fails_closed(tmp_path, monkeypatch):
    monkeypatch.setattr(vault.sys, "platform", "linux")
    store = vault.WindowsCredentialVault(tmp_path)
    with pytest.raises(vault.CredentialVaultUnavailable, match="windows_dpapi_required"):
        store.save("binance", {"api_key": "key", "api_secret": "secret"})
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("venue,credentials", [
    ("binance", {"api_key": "binance-key", "api_secret": "binance-secret"}),
    ("okx", {"api_key": "okx-key", "api_secret": "okx-secret", "passphrase": "phrase"}),
])
def test_round_trip_and_metadata_never_contain_secrets(tmp_path, monkeypatch, venue, credentials):
    _fake_dpapi(monkeypatch)
    store = vault.WindowsCredentialVault(tmp_path)
    metadata = store.save(venue, credentials)
    assert store.load(venue) == credentials
    assert metadata["venue"] == venue
    assert metadata["configured"] if "configured" in metadata else metadata["key_fingerprint"]
    raw_files = [path.read_bytes() for path in tmp_path.iterdir()]
    for value in credentials.values():
        assert all(value.encode() not in raw for raw in raw_files)
    assert store.metadata(venue)["configured"] is True
    assert store.delete(venue) is True
    assert store.metadata(venue) is None
    with pytest.raises(FileNotFoundError):
        store.load(venue)


def test_rejects_unknown_venues_and_extra_fields(tmp_path, monkeypatch):
    _fake_dpapi(monkeypatch)
    store = vault.WindowsCredentialVault(tmp_path)
    with pytest.raises(ValueError, match="unsupported_exchange_venue"):
        store.save("coinbase", {"api_key": "key", "api_secret": "secret"})
    with pytest.raises(ValueError, match="invalid_exchange_credential_fields"):
        store.save("binance", {"api_key": "key", "api_secret": "secret", "password": "x"})


@pytest.mark.parametrize("credentials", [
    {"api_key": "", "api_secret": "secret"},
    {"api_key": " key ", "api_secret": "secret"},
    {"api_key": "key\n", "api_secret": "secret"},
    {"api_key": "key", "api_secret": "secret", "passphrase": "unexpected"},
])
def test_rejects_invalid_values(tmp_path, monkeypatch, credentials):
    _fake_dpapi(monkeypatch)
    store = vault.WindowsCredentialVault(tmp_path)
    with pytest.raises(ValueError):
        store.save("binance", credentials)


def test_corrupt_or_wrong_venue_payload_fails_closed(tmp_path, monkeypatch):
    _fake_dpapi(monkeypatch)
    store = vault.WindowsCredentialVault(tmp_path)
    store.save("binance", {"api_key": "key", "api_secret": "secret"})
    blob, _ = store._paths("binance")
    blob.write_bytes(b"corrupt")
    with pytest.raises(vault.CredentialVaultCorrupt):
        store.load("binance")


def test_metadata_contains_only_fingerprint_and_non_secret_fields(tmp_path, monkeypatch):
    _fake_dpapi(monkeypatch)
    store = vault.WindowsCredentialVault(tmp_path)
    store.save("okx", {"api_key": "okx-private-key", "api_secret": "secret", "passphrase": "private-pass"})
    _, metadata_path = store._paths("okx")
    metadata = json.loads(metadata_path.read_text())
    assert set(metadata) == {"version", "venue", "key_fingerprint", "updated_at"}
    assert "okx-private-key" not in metadata_path.read_text()
    assert "private-pass" not in metadata_path.read_text()
