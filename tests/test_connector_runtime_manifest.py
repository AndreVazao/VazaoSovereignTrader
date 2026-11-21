from __future__ import annotations

import os
from pathlib import Path

import pytest

from PC_ENGINE.core.connector_runtime_manifest import (
    RuntimeManifestError,
    RuntimeMount,
    build_runtime_manifest,
    revalidate_runtime_manifest,
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
        required_files=[loader],
        required_directories=[stdlib],
    )

    assert manifest.executable == executable
    assert [(item.source, item.destination, item.is_directory) for item in manifest.mounts] == [
        (executable, executable, False),
        (loader, loader, False),
        (stdlib, stdlib, True),
    ]
    # Files inside an explicitly mounted directory are exposed by that
    # directory mount; they must not also be listed as individual mounts.


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



def test_runtime_manifest_rejects_hard_linked_runtime_file(tmp_path):
    executable = _executable(tmp_path / "python")
    library = tmp_path / "library.so"
    library.write_bytes(b"library")
    alias = tmp_path / "library-alias.so"
    alias.hardlink_to(library)

    with pytest.raises(RuntimeManifestError, match="runtime_file_must_not_be_hard_linked"):
        build_runtime_manifest(executable, required_files=[library])


def test_runtime_manifest_rejects_group_or_world_writable_file(tmp_path):
    executable = _executable(tmp_path / "python")
    library = tmp_path / "library.so"
    library.write_bytes(b"library")
    library.chmod(0o666)

    with pytest.raises(
        RuntimeManifestError,
        match="runtime_file_must_not_be_group_or_world_writable",
    ):
        build_runtime_manifest(executable, required_files=[library])


def test_runtime_manifest_rejects_group_or_world_writable_directory(tmp_path):
    executable = _executable(tmp_path / "python")
    runtime = tmp_path / "stdlib"
    runtime.mkdir()
    runtime.chmod(0o777)

    with pytest.raises(
        RuntimeManifestError,
        match="runtime_directory_must_not_be_group_or_world_writable",
    ):
        build_runtime_manifest(executable, required_directories=[runtime])



def test_runtime_manifest_rejects_symlink_inside_directory_mount(tmp_path):
    executable = _executable(tmp_path / "python")
    runtime = tmp_path / "stdlib"
    runtime.mkdir()
    target = tmp_path / "outside-secret"
    target.write_text("not part of the runtime", encoding="utf-8")
    (runtime / "escape").symlink_to(target)

    with pytest.raises(
        RuntimeManifestError,
        match="runtime_directory_contains_symlink",
    ):
        build_runtime_manifest(executable, required_directories=[runtime])


def test_runtime_manifest_rejects_hard_link_inside_directory_mount(tmp_path):
    executable = _executable(tmp_path / "python")
    runtime = tmp_path / "stdlib"
    runtime.mkdir()
    library = runtime / "library.so"
    library.write_bytes(b"library")
    alias = tmp_path / "outside-alias.so"
    alias.hardlink_to(library)

    with pytest.raises(
        RuntimeManifestError,
        match="runtime_directory_contains_hard_linked_file",
    ):
        build_runtime_manifest(executable, required_directories=[runtime])


def test_runtime_manifest_rejects_nested_group_or_world_writable_file(tmp_path):
    executable = _executable(tmp_path / "python")
    runtime = tmp_path / "stdlib"
    nested = runtime / "package"
    nested.mkdir(parents=True)
    library = nested / "extension.so"
    library.write_bytes(b"extension")
    library.chmod(0o666)

    with pytest.raises(
        RuntimeManifestError,
        match="runtime_directory_contains_writable_file",
    ):
        build_runtime_manifest(executable, required_directories=[runtime])


def test_runtime_manifest_rejects_nested_group_or_world_writable_directory(tmp_path):
    executable = _executable(tmp_path / "python")
    runtime = tmp_path / "stdlib"
    nested = runtime / "package"
    nested.mkdir(parents=True)
    nested.chmod(0o777)

    with pytest.raises(
        RuntimeManifestError,
        match="runtime_directory_contains_writable_directory",
    ):
        build_runtime_manifest(executable, required_directories=[runtime])


def test_runtime_manifest_rejects_special_file_inside_directory_mount(tmp_path):
    if not hasattr(os, "mkfifo"):
        pytest.skip("FIFO creation is unavailable on this platform")
    executable = _executable(tmp_path / "python")
    runtime = tmp_path / "stdlib"
    runtime.mkdir()
    os.mkfifo(runtime / "unexpected-pipe")

    with pytest.raises(
        RuntimeManifestError,
        match="runtime_directory_contains_special_file",
    ):
        build_runtime_manifest(executable, required_directories=[runtime])



def test_runtime_manifest_supports_explicit_loader_alias_destination(tmp_path):
    executable = _executable(tmp_path / "python")
    loader_source = tmp_path / "lib" / "ld-linux-x86-64.so.2"
    loader_source.parent.mkdir()
    loader_source.write_bytes(b"trusted-loader")
    loader_source.chmod(0o444)
    loader_destination = Path("/lib64/ld-linux-x86-64.so.2")

    manifest = build_runtime_manifest(
        executable,
        required_mounts=[
            RuntimeMount(loader_source, loader_destination, False),
        ],
    )

    assert manifest.mounts[1] == RuntimeMount(
        loader_source,
        loader_destination,
        False,
    )
    assert revalidate_runtime_manifest(manifest) == manifest


def test_runtime_manifest_builder_mounts_alias_at_guest_loader_path(tmp_path):
    executable = _executable(tmp_path / "python")
    python_home = tmp_path / "python-home"
    python_home.mkdir()
    python_home.chmod(0o555)
    loader_source = tmp_path / "lib" / "ld-linux-x86-64.so.2"
    loader_source.parent.mkdir()
    loader_source.write_bytes(b"trusted-loader")
    loader_source.chmod(0o444)
    loader_destination = Path("/lib64/ld-linux-x86-64.so.2")
    manifest = build_runtime_manifest(
        executable,
        required_directories=[python_home],
        required_mounts=[
            RuntimeMount(loader_source, loader_destination, False),
        ],
    )

    from PC_ENGINE.core.connector_worker_sandbox import build_linux_bwrap_command

    argv = build_linux_bwrap_command(
        [str(executable), "--version"],
        runtime_manifest=manifest,
        python_home=str(python_home),
        bwrap_path=_executable(tmp_path / "bwrap"),
    )

    mount_index = next(
        index
        for index, item in enumerate(argv)
        if item == "--ro-bind" and argv[index + 1] == str(loader_source)
    )
    assert argv[mount_index + 1 : mount_index + 3] == [
        str(loader_source),
        str(loader_destination),
    ]
    assert argv.index("--dir") < mount_index
    assert "/lib64" in argv


@pytest.mark.parametrize(
    ("destination", "message"),
    [
        (Path("relative/loader"), "runtime_mount_destination_must_be_absolute"),
        (Path("/lib/../etc/passwd"), "runtime_mount_destination_not_normalized"),
        ("/lib//loader", "runtime_mount_destination_not_normalized"),
        (Path("/proc/loader"), "runtime_mount_destination_is_reserved"),
        (Path("/tmp/loader"), "runtime_mount_destination_is_reserved"),
        (Path("/work/loader"), "runtime_mount_destination_is_reserved"),
    ],
)
def test_runtime_manifest_rejects_unsafe_alias_destinations(
    tmp_path,
    destination,
    message,
):
    executable = _executable(tmp_path / "python")
    source = tmp_path / "loader"
    source.write_bytes(b"loader")
    source.chmod(0o444)

    with pytest.raises(RuntimeManifestError, match=message):
        build_runtime_manifest(
            executable,
            required_mounts=[RuntimeMount(source, destination, False)],
        )


def test_runtime_manifest_rejects_duplicate_alias_destinations(tmp_path):
    executable = _executable(tmp_path / "python")
    first = tmp_path / "first-loader"
    second = tmp_path / "second-loader"
    first.write_bytes(b"first")
    second.write_bytes(b"second")
    first.chmod(0o444)
    second.chmod(0o444)
    destination = Path("/lib64/ld-linux-x86-64.so.2")

    with pytest.raises(
        RuntimeManifestError,
        match="duplicate_runtime_mount_destination",
    ):
        build_runtime_manifest(
            executable,
            required_mounts=[
                RuntimeMount(first, destination, False),
                RuntimeMount(second, destination, False),
            ],
        )


def test_runtime_manifest_rejects_alias_source_covered_by_directory_mount(tmp_path):
    executable = _executable(tmp_path / "python")
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    loader = runtime / "loader"
    loader.write_bytes(b"loader")
    loader.chmod(0o444)

    with pytest.raises(
        RuntimeManifestError,
        match="runtime_file_covered_by_directory_mount",
    ):
        build_runtime_manifest(
            executable,
            required_directories=[runtime],
            required_mounts=[
                RuntimeMount(loader, Path("/lib64/loader"), False),
            ],
        )
