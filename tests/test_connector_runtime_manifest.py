from __future__ import annotations

from pathlib import Path

import pytest

from PC_ENGINE.core.connector_runtime_manifest import (
    RuntimeManifestError,
    build_runtime_manifest,
)


def _executable(path: Path) -> Path:
    path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    path.chmod(0o700)
    return path


def test_runtime_manifest_contains_only_explicit_read_only_paths(tmp_path):
    executable = _executable(tmp_path / "python")
    loader = tmp_path / "ld-linux.so"
    loader.write_bytes(b"loader")
    stdlib = tmp_path / "python-stdlib"
    stdlib.mkdir()
    extension = stdlib / "extension.so"
    extension.write_bytes(b"extension")

    manifest = build_runtime_manifest(
        executable,
        required_files=[loader, extension],
        required_directories=[stdlib],
    )

    assert manifest.executable == executable
    assert [(item.source, item.destination, item.is_directory) for item in manifest.mounts] == [
        (executable, executable, False),
        (loader, loader, False),
        (extension, extension, False),
        (stdlib, stdlib, True),
    ]


@pytest.mark.parametrize(
    "directory",
    [Path("/"), Path("/usr"), Path("/usr/bin"), Path("/usr/lib"), Path("/usr/local"),
     Path("/etc"), Path("/home"), Path("/var"), Path("/proc"), Path("/sys"),
     Path("/dev"), Path("/tmp"), Path("/mnt")],
)
def test_runtime_manifest_rejects_broad_or_sensitive_directory_mounts(tmp_path, directory):
    executable = _executable(tmp_path / "python")
    if not directory.exists():
        pytest.skip(f"{directory} is absent on this runner")
    with pytest.raises(RuntimeManifestError, match="runtime_directory_is_too_broad"):
        build_runtime_manifest(executable, required_directories=[directory])


def test_runtime_manifest_rejects_symlinked_executable(tmp_path):
    target = _executable(tmp_path / "real-python")
    link = tmp_path / "python"
    link.symlink_to(target)
    with pytest.raises(RuntimeManifestError, match="runtime_executable_must_not_use_symlinks"):
        build_runtime_manifest(link)


def test_runtime_manifest_rejects_symlinked_runtime_file(tmp_path):
    executable = _executable(tmp_path / "python")
    target = tmp_path / "real-library.so"
    target.write_bytes(b"library")
    link = tmp_path / "library.so"
    link.symlink_to(target)
    with pytest.raises(RuntimeManifestError, match="runtime_file_must_not_use_symlinks"):
        build_runtime_manifest(executable, required_files=[link])


def test_runtime_manifest_rejects_duplicate_files_and_directories(tmp_path):
    executable = _executable(tmp_path / "python")
    library = tmp_path / "lib.so"
    library.write_bytes(b"library")
    directory = tmp_path / "stdlib"
    directory.mkdir()

    with pytest.raises(RuntimeManifestError, match="duplicate_runtime_file"):
        build_runtime_manifest(executable, required_files=[library, library])
    with pytest.raises(RuntimeManifestError, match="duplicate_runtime_directory"):
        build_runtime_manifest(executable, required_directories=[directory, directory])


def test_runtime_manifest_rejects_non_absolute_and_missing_paths(tmp_path):
    executable = _executable(tmp_path / "python")
    with pytest.raises(RuntimeManifestError, match="runtime_file_must_be_absolute"):
        build_runtime_manifest(executable, required_files=["relative-library.so"])
    with pytest.raises(RuntimeManifestError, match="runtime_file_does_not_exist"):
        build_runtime_manifest(executable, required_files=[tmp_path / "missing.so"])


def test_runtime_manifest_rejects_non_regular_runtime_file(tmp_path):
    executable = _executable(tmp_path / "python")
    directory = tmp_path / "not-a-file"
    directory.mkdir()
    with pytest.raises(RuntimeManifestError, match="runtime_file_must_be_regular_file"):
        build_runtime_manifest(executable, required_files=[directory])


def test_runtime_manifest_rejects_non_executable_interpreter(tmp_path):
    executable = tmp_path / "python"
    executable.write_text("not executable", encoding="utf-8")
    executable.chmod(0o600)
    with pytest.raises(RuntimeManifestError, match="runtime_executable_not_executable"):
        build_runtime_manifest(executable)


def test_runtime_manifest_rejects_file_hidden_inside_directory_mount(tmp_path):
    executable = _executable(tmp_path / "python")
    runtime = tmp_path / "stdlib"
    runtime.mkdir()
    nested = runtime / "extension.so"
    nested.write_bytes(b"extension")

    with pytest.raises(RuntimeManifestError, match="runtime_file_covered_by_directory_mount"):
        build_runtime_manifest(
            executable,
            required_files=[nested],
            required_directories=[runtime],
        )


def test_runtime_manifest_rejects_executable_hidden_inside_directory_mount(tmp_path):
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    executable = _executable(runtime / "python")

    with pytest.raises(RuntimeManifestError, match="runtime_file_covered_by_directory_mount"):
        build_runtime_manifest(executable, required_directories=[runtime])


def test_runtime_manifest_rejects_nested_directory_mounts(tmp_path):
    executable = _executable(tmp_path / "python")
    runtime = tmp_path / "stdlib"
    nested = runtime / "lib-dynload"
    nested.mkdir(parents=True)

    with pytest.raises(RuntimeManifestError, match="overlapping_runtime_directories"):
        build_runtime_manifest(
            executable,
            required_directories=[runtime, nested],
        )
