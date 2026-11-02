"""Stable user-data vault outside the install directory.

The vault is deliberately separate from versioned application files so an
installer upgrade or uninstall can preserve learning state. This module only
resolves paths and writes a non-secret manifest; it never migrates, deletes,
restores, or uploads learning data automatically.
"""
from __future__ import annotations

import json
import os
import platform
import tempfile
import time
from pathlib import Path
from typing import Any


VAULT_DIRNAME = "VazaoSovereignTrader"
MANIFEST_FILENAME = "vault_manifest.json"
VAULT_SCHEMA_VERSION = 1


def default_vault_path(
    *,
    environ: dict[str, str] | None = None,
    system: str | None = None,
    home: str | Path | None = None,
) -> Path:
    """Return a stable per-user vault path, never inside the install directory."""
    env = os.environ if environ is None else environ
    os_name = (system or platform.system()).lower()
    if os_name == "windows":
        base = env.get("LOCALAPPDATA") or env.get("APPDATA")
        if base:
            return Path(base).expanduser() / VAULT_DIRNAME / "vault"
    if os_name == "darwin":
        return Path(home or Path.home()).expanduser() / "Library" / "Application Support" / VAULT_DIRNAME / "vault"
    xdg = env.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg).expanduser() / VAULT_DIRNAME.lower() / "vault"
    return Path(home or Path.home()).expanduser() / ".local" / "share" / VAULT_DIRNAME.lower() / "vault"


def vault_layout(root: str | Path) -> dict[str, Path]:
    """Canonical data layout shared by app versions."""
    base = Path(root).expanduser().resolve()
    return {
        "root": base,
        "learning": base / "learning",
        "backups": base / "backups",
        "imports": base / "imports",
        "exports": base / "exports",
        "logs": base / "logs",
        "manifest": base / MANIFEST_FILENAME,
    }


def initialize_vault(root: str | Path | None = None) -> dict[str, Any]:
    """Create stable vault folders and atomically create/update a minimal manifest."""
    paths = vault_layout(root if root is not None else default_vault_path())
    for key in ("root", "learning", "backups", "imports", "exports", "logs"):
        paths[key].mkdir(parents=True, exist_ok=True)

    manifest_path = paths["manifest"]
    existing: dict[str, Any] | None = None
    if manifest_path.exists():
        try:
            loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict) and loaded.get("schema_version") == VAULT_SCHEMA_VERSION:
                existing = loaded
        except (OSError, UnicodeError, json.JSONDecodeError):
            existing = None

    if existing is None:
        existing = {
            "schema_version": VAULT_SCHEMA_VERSION,
            "product": "VazaoSovereignTrader",
            "created_at_unix": int(time.time()),
            "updated_at_unix": int(time.time()),
            "preservation_policy": "preserve_on_upgrade_and_uninstall",
            "contents": {
                "learning": "persistent learning records; never execution authorization",
                "backups": "verified recovery snapshots",
                "imports": "quarantined candidate imports; not auto-applied",
                "exports": "explicit user-requested exports",
                "logs": "diagnostic logs; redact secrets before sharing",
            },
        }
    else:
        existing["updated_at_unix"] = int(time.time())

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".vault_manifest.", suffix=".tmp", dir=paths["root"]
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(existing, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, manifest_path)
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
    return {"root": str(paths["root"]), "paths": {key: str(value) for key, value in paths.items()}, "manifest": existing}


def validate_vault(root: str | Path) -> dict[str, Any]:
    """Read-only vault validation; it never creates or repairs anything."""
    paths = vault_layout(root)
    result: dict[str, Any] = {"status": "missing", "root": str(paths["root"]), "checks": {}}
    if not paths["root"].is_dir():
        result["reason"] = "vault_directory_missing"
        return result
    manifest = paths["manifest"]
    if not manifest.is_file():
        result["status"] = "degraded"
        result["reason"] = "vault_manifest_missing"
        return result
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        result["status"] = "invalid"
        result["reason"] = type(exc).__name__
        return result
    if not isinstance(payload, dict) or payload.get("schema_version") != VAULT_SCHEMA_VERSION:
        result["status"] = "invalid"
        result["reason"] = "unsupported_manifest_schema"
        return result
    result["checks"] = {
        key: paths[key].is_dir()
        for key in ("learning", "backups", "imports", "exports", "logs")
    }
    result["status"] = "healthy" if all(result["checks"].values()) else "degraded"
    result["reason"] = None if result["status"] == "healthy" else "vault_subdirectory_missing"
    result["manifest"] = payload
    return result
