from __future__ import annotations

import json
from pathlib import Path

from PC_ENGINE.core.data_vault import (
    MANIFEST_FILENAME,
    VAULT_DIRNAME,
    default_vault_path,
    legacy_vault_path,
    initialize_vault,
    validate_vault,
)


def test_windows_vault_is_outside_install_and_uses_stable_user_data_path(tmp_path: Path):
    path = default_vault_path(
        environ={"LOCALAPPDATA": str(tmp_path / "AppData" / "Local")},
        system="Windows",
        home=tmp_path,
    )
    assert path == tmp_path / "AppData" / "Local" / "VazaoSovereignTraderData" / "vault"
    assert path != tmp_path / "AppData" / "Local" / "VazaoSovereignTrader" / "vault"
    assert "Program Files" not in str(path)



def test_legacy_windows_vault_is_discoverable_without_being_the_new_default(tmp_path: Path):
    env = {"LOCALAPPDATA": str(tmp_path / "AppData" / "Local")}
    current = default_vault_path(environ=env, system="Windows", home=tmp_path)
    legacy = legacy_vault_path(environ=env, system="Windows", home=tmp_path)
    assert legacy == tmp_path / "AppData" / "Local" / "VazaoSovereignTrader" / "vault"
    assert current != legacy


def test_linux_vault_respects_xdg_data_home(tmp_path: Path):
    path = default_vault_path(
        environ={"XDG_DATA_HOME": str(tmp_path / "xdg")},
        system="Linux",
        home=tmp_path,
    )
    assert path == tmp_path / "xdg" / "vazaosovereigntraderdata" / "vault"


def test_initialize_vault_creates_layout_and_validates(tmp_path: Path):
    root = tmp_path / "persistent-vault"
    result = initialize_vault(root)
    assert Path(result["root"]) == root.resolve()
    assert validate_vault(root)["status"] == "healthy"
    assert (root / MANIFEST_FILENAME).is_file()
    assert (root / "learning").is_dir()
    assert (root / "backups").is_dir()


def test_initialize_vault_preserves_existing_learning_files_and_creation_time(tmp_path: Path):
    root = tmp_path / "vault"
    initialize_vault(root)
    learning_db = root / "learning" / "learning.sqlite3"
    learning_db.write_bytes(b"existing-test-data")
    first = json.loads((root / MANIFEST_FILENAME).read_text(encoding="utf-8"))
    second = initialize_vault(root)
    after = json.loads((root / MANIFEST_FILENAME).read_text(encoding="utf-8"))
    assert learning_db.read_bytes() == b"existing-test-data"
    assert after["created_at_unix"] == first["created_at_unix"]
    assert second["manifest"]["preservation_policy"] == "preserve_on_upgrade_and_uninstall"


def test_validate_vault_is_read_only_when_missing(tmp_path: Path):
    root = tmp_path / "not-created"
    result = validate_vault(root)
    assert result["status"] == "missing"
    assert not root.exists()


def test_validate_vault_rejects_corrupt_manifest(tmp_path: Path):
    root = tmp_path / "vault"
    initialize_vault(root)
    (root / MANIFEST_FILENAME).write_text("{broken", encoding="utf-8")
    result = validate_vault(root)
    assert result["status"] == "invalid"
    assert result["reason"] == "JSONDecodeError"
