from pathlib import Path

from PC_ENGINE.core import config as config_module


def test_frozen_paths_move_pc_engine_data_beside_exe(monkeypatch, tmp_path):
    monkeypatch.setattr(config_module.sys, "frozen", True, raising=False)
    monkeypatch.setattr(config_module, "RUNTIME_ROOT", tmp_path)
    source = {
        "data_dir": "PC_ENGINE/data/radar",
        "nested": {"path": "PC_ENGINE/data/research/file.json"},
        "plain": "keep",
        "items": ["PC_ENGINE/data/a", "other"],
    }
    result = config_module._rewrite_frozen_paths(source)
    assert result["data_dir"] == str(tmp_path / "data/radar")
    assert result["nested"]["path"] == str(tmp_path / "data/research/file.json")
    assert result["plain"] == "keep"
    assert result["items"][0] == str(tmp_path / "data/a")
