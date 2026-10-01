from __future__ import annotations

import base64
import os
from pathlib import Path


_ALIAS = "vazao_sovereign_trader_mobile_device_token_v1"


def _android_crypto():
    from jnius import autoclass, jarray

    KeyStore = autoclass("java.security.KeyStore")
    KeyGenerator = autoclass("javax.crypto.KeyGenerator")
    KeyProperties = autoclass("android.security.keystore.KeyProperties")
    Cipher = autoclass("javax.crypto.Cipher")
    GCMParameterSpec = autoclass("javax.crypto.spec.GCMParameterSpec")
    return autoclass, KeyStore, KeyGenerator, KeyProperties, Cipher, GCMParameterSpec, jarray


def _to_java_bytes(data: bytes, jarray):
    return jarray("b")([value if value < 128 else value - 256 for value in data])


def _from_java_bytes(data) -> bytes:
    return bytes((int(value) & 0xFF) for value in data)


def save_device_token(path: str | Path, token: str) -> bool:
    """Encrypt a token with a non-exportable Android Keystore AES-GCM key.

    Returns False outside Android or when secure storage is unavailable. It never
    falls back to plaintext storage.
    """
    if not token:
        return False
    try:
        autoclass, KeyStore, KeyGenerator, KeyProperties, Cipher, _, jarray = _android_crypto()
        store = KeyStore.getInstance("AndroidKeyStore")
        store.load(None)
        if not store.containsAlias(_ALIAS):
            generator = KeyGenerator.getInstance("AES", "AndroidKeyStore")
            builder_cls = autoclass("android.security.keystore.KeyGenParameterSpec$Builder")
            builder = builder_cls(_ALIAS, 3)
            builder.setBlockModes(jarray("java.lang.String")(["GCM"]))
            builder.setEncryptionPaddings(jarray("java.lang.String")(["NoPadding"]))
            builder.setRandomizedEncryptionRequired(True)
            generator.init(builder.build())
            generator.generateKey()
        key = store.getKey(_ALIAS, None)
        cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, key)
        encrypted = _from_java_bytes(cipher.doFinal(_to_java_bytes(token.encode("utf-8"), jarray)))
        iv = _from_java_bytes(cipher.getIV())
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(".tmp")
        temp.write_text(base64.b64encode(iv + encrypted).decode("ascii"), encoding="ascii")
        os.replace(temp, path)
        return True
    except Exception:
        return False


def load_device_token(path: str | Path) -> str:
    """Return the decrypted token, or an empty string without plaintext fallback."""
    try:
        path = Path(path)
        if not path.is_file():
            return ""
        packed = base64.b64decode(path.read_text(encoding="ascii"), validate=True)
        if len(packed) < 13:
            return ""
        iv, encrypted = packed[:12], packed[12:]
        _, KeyStore, _, _, Cipher, GCMParameterSpec, jarray = _android_crypto()
        store = KeyStore.getInstance("AndroidKeyStore")
        store.load(None)
        key = store.getKey(_ALIAS, None)
        if key is None:
            return ""
        cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.DECRYPT_MODE, key, GCMParameterSpec(128, _to_java_bytes(iv, jarray)))
        plain = _from_java_bytes(cipher.doFinal(_to_java_bytes(encrypted, jarray)))
        return plain.decode("utf-8")
    except Exception:
        return ""


def delete_device_token(path: str | Path) -> None:
    try:
        Path(path).unlink(missing_ok=True)
    except OSError:
        pass
    try:
        _, KeyStore, _, _, _, _, _ = _android_crypto()
        store = KeyStore.getInstance("AndroidKeyStore")
        store.load(None)
        if store.containsAlias(_ALIAS):
            store.deleteEntry(_ALIAS)
    except Exception:
        pass
