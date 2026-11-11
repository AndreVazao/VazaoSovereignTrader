from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


class CredentialVaultError(RuntimeError):
    """Base error for local exchange credential storage."""


class CredentialVaultUnavailable(CredentialVaultError):
    """Raised when the platform cannot provide the required encryption."""


class CredentialVaultCorrupt(CredentialVaultError):
    """Raised when encrypted credential storage cannot be decoded safely."""


_ALLOWED_VENUES = frozenset({"binance", "okx"})
_ALLOWED_FIELDS = {
    "binance": frozenset({"api_key", "api_secret"}),
    "okx": frozenset({"api_key", "api_secret", "passphrase"}),
}
_SAFE_VENUE = re.compile(r"^[a-z]+$")


def _dpapi_protect(data: bytes) -> bytes:
    """Encrypt bytes with Windows DPAPI CurrentUser scope (never machine scope)."""
    if sys.platform != "win32":
        raise CredentialVaultUnavailable("windows_dpapi_required")

    import ctypes
    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]

    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    crypt32.CryptProtectData.argtypes = [
        ctypes.POINTER(DATA_BLOB), wintypes.LPCWSTR, ctypes.c_void_p,
        ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(DATA_BLOB),
    ]
    crypt32.CryptProtectData.restype = wintypes.BOOL
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p
    source_buffer = ctypes.create_string_buffer(data)
    source = DATA_BLOB(len(data), ctypes.cast(source_buffer, ctypes.POINTER(ctypes.c_byte)))
    output = DATA_BLOB()
    # CRYPTPROTECT_UI_FORBIDDEN; omit LOCAL_MACHINE so data is bound to current user.
    if not crypt32.CryptProtectData(
        ctypes.byref(source), ctypes.c_wchar_p("VST exchange credential"), None, None, None, 0x1,
        ctypes.byref(output),
    ):
        raise CredentialVaultUnavailable("dpapi_protect_failed")
    try:
        return ctypes.string_at(output.pbData, output.cbData)
    finally:
        kernel32.LocalFree(ctypes.cast(output.pbData, ctypes.c_void_p))


def _dpapi_unprotect(data: bytes) -> bytes:
    """Decrypt bytes with the current Windows user's DPAPI context."""
    if sys.platform != "win32":
        raise CredentialVaultUnavailable("windows_dpapi_required")

    import ctypes
    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]

    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    crypt32.CryptUnprotectData.argtypes = [
        ctypes.POINTER(DATA_BLOB), ctypes.POINTER(wintypes.LPWSTR), ctypes.c_void_p,
        ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(DATA_BLOB),
    ]
    crypt32.CryptUnprotectData.restype = wintypes.BOOL
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p
    source_buffer = ctypes.create_string_buffer(data)
    source = DATA_BLOB(len(data), ctypes.cast(source_buffer, ctypes.POINTER(ctypes.c_byte)))
    output = DATA_BLOB()
    description = wintypes.LPWSTR()
    if not crypt32.CryptUnprotectData(
        ctypes.byref(source), ctypes.byref(description), None, None, None, 0x1,
        ctypes.byref(output),
    ):
        raise CredentialVaultCorrupt("dpapi_unprotect_failed")
    try:
        return ctypes.string_at(output.pbData, output.cbData)
    finally:
        kernel32.LocalFree(ctypes.cast(output.pbData, ctypes.c_void_p))
        if description:
            kernel32.LocalFree(ctypes.cast(description, ctypes.c_void_p))


class WindowsCredentialVault:
    """Small DPAPI CurrentUser vault; unsupported systems fail closed.

    Only Binance/OKX credential records are accepted. The credential payload is
    encrypted as one JSON document; the adjacent metadata file contains only a
    non-reversible API-key fingerprint and timestamp.
    """

    VERSION = 1
    MAX_SECRET_LENGTH = 4096

    def __init__(self, root: str | Path):
        self.root = Path(root)

    @staticmethod
    def _venue(value: str) -> str:
        venue = str(value or "").strip().lower()
        if venue not in _ALLOWED_VENUES or not _SAFE_VENUE.fullmatch(venue):
            raise ValueError("unsupported_exchange_venue")
        return venue

    @classmethod
    def _validate_credentials(cls, venue: str, credentials: dict[str, Any]) -> dict[str, str]:
        if not isinstance(credentials, dict) or set(credentials) != set(_ALLOWED_FIELDS[venue]):
            raise ValueError("invalid_exchange_credential_fields")
        result: dict[str, str] = {}
        for field in _ALLOWED_FIELDS[venue]:
            value = credentials.get(field)
            if not isinstance(value, str) or not value or len(value) > cls.MAX_SECRET_LENGTH:
                raise ValueError("invalid_exchange_credential_value")
            if value.strip() != value or any(ord(char) < 32 for char in value):
                raise ValueError("invalid_exchange_credential_value")
            result[field] = value
        return result

    def _paths(self, venue: str) -> tuple[Path, Path]:
        name = self._venue(venue)
        return self.root / (name + ".dpapi"), self.root / (name + ".metadata.json")

    @staticmethod
    def _atomic_write(path: Path, data: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=".vst-credential-", dir=str(path.parent))
        temp = Path(temp_name)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.chmod(temp, 0o600)
            except OSError:
                pass
            os.replace(temp, path)
        finally:
            try:
                temp.unlink(missing_ok=True)
            except OSError:
                pass

    def save(self, venue: str, credentials: dict[str, Any]) -> dict[str, Any]:
        name = self._venue(venue)
        clean = self._validate_credentials(name, credentials)
        payload = json.dumps(
            {"version": self.VERSION, "venue": name, "credentials": clean},
            sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        ).encode("utf-8")
        encrypted = _dpapi_protect(payload)
        vault_path, metadata_path = self._paths(name)
        metadata = {
            "version": self.VERSION,
            "venue": name,
            "key_fingerprint": hashlib.sha256(clean["api_key"].encode("utf-8")).hexdigest()[:20],
            "updated_at": int(time.time()),
        }
        self._atomic_write(vault_path, encrypted)
        self._atomic_write(
            metadata_path,
            (json.dumps(metadata, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8"),
        )
        return dict(metadata)

    def load(self, venue: str) -> dict[str, str]:
        name = self._venue(venue)
        vault_path, _ = self._paths(name)
        try:
            encrypted = vault_path.read_bytes()
        except FileNotFoundError:
            raise
        if not encrypted:
            raise CredentialVaultCorrupt("empty_credential_blob")
        try:
            payload = json.loads(_dpapi_unprotect(encrypted).decode("utf-8"))
        except CredentialVaultError:
            raise
        except Exception as exc:
            raise CredentialVaultCorrupt("credential_payload_invalid") from exc
        if not isinstance(payload, dict) or payload.get("version") != self.VERSION or payload.get("venue") != name:
            raise CredentialVaultCorrupt("credential_payload_identity_invalid")
        return self._validate_credentials(name, payload.get("credentials"))

    def metadata(self, venue: str) -> dict[str, Any] | None:
        name = self._venue(venue)
        _, metadata_path = self._paths(name)
        try:
            payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise CredentialVaultCorrupt("credential_metadata_invalid") from exc
        if (
            not isinstance(payload, dict) or payload.get("version") != self.VERSION
            or payload.get("venue") != name
            or not re.fullmatch(r"[0-9a-f]{20}", str(payload.get("key_fingerprint", "")))
        ):
            raise CredentialVaultCorrupt("credential_metadata_identity_invalid")
        return {
            "venue": name,
            "key_fingerprint": payload["key_fingerprint"],
            "updated_at": int(payload.get("updated_at", 0)),
            "configured": True,
        }

    def delete(self, venue: str) -> bool:
        vault_path, metadata_path = self._paths(venue)
        existed = vault_path.exists() or metadata_path.exists()
        for path in (vault_path, metadata_path):
            try:
                path.unlink(missing_ok=True)
            except OSError as exc:
                raise CredentialVaultError("credential_delete_failed") from exc
        return existed
