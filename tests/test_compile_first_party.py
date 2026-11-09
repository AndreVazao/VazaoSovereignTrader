from __future__ import annotations

from scripts.compile_first_party import collect_first_party_python_files


def test_compile_helper_excludes_virtual_environments_and_caches(tmp_path):
    root = tmp_path / "PC_ENGINE"
    (root / "core").mkdir(parents=True)
    (root / ".venv" / "Lib").mkdir(parents=True)
    (root / "__pycache__").mkdir()
    (root / "core" / "engine.py").write_text("VALUE = 1\n", encoding="utf-8")
    (root / ".venv" / "Lib" / "site.py").write_text("raise RuntimeError()\n", encoding="utf-8")
    (root / "__pycache__" / "ignored.py").write_text("raise RuntimeError()\n", encoding="utf-8")

    files = collect_first_party_python_files(root)

    assert files == [root / "core" / "engine.py"]


def test_compile_helper_rejects_missing_source_root(tmp_path):
    missing = tmp_path / "missing"

    try:
        collect_first_party_python_files(missing)
    except NotADirectoryError:
        pass
    else:
        raise AssertionError("missing source roots must fail explicitly")
