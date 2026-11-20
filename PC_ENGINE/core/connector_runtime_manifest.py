from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


class RuntimeManifestError(ValueError):
    """Raised when a connector runtime manifest is unsafe or incomplete."""


# These roots are deliberately too broad to be accepted as a runtime entry.
# A manifest must enumerate the interpreter, libraries and runtime directories.
_FORBIDDEN_DIRECTORY_MOUNTS = {
    Path("/"),
    Path("/usr"),
    Path("/usr/bin"),
    Path("/usr/sbin"),
    Path("/usr/lib"),
    Path("/usr/lib64"),
    Path("/usr/local"),
    Path("/lib"),
    Path("/lib64"),
    Path("/bin"),
    Path("/sbin"),
    Path("/etc"),
    Path("/home"),
    Path("/root"),
    Path("/var"),
    Path("/run"),
    Path("/proc"),
    Path("/sys"),
    Path("/dev"),
    Path("/tmp"),
    Path("/mnt"),
    Path("/media"),
}


@dataclass(frozen=True, slots=True)
class RuntimeMount:
    """One immutable host path to expose read-only at its same absolute path."""

    source: Path
    destination: Path
    is_directory: bool


@dataclass(frozen=True, slots=True)
class RuntimeManifest:
    """Explicit minimal runtime closure for one connector worker process."""

    executable: Path
    mounts: tuple[RuntimeMount, ...]


def _canonical_path(value: str | os.PathLike[str], *, label: str) -> Path:
    raw = Path(value)
    if not raw.is_absolute():
        raise RuntimeManifestError(f"{label}_must_be_absolute")
    try:
        resolved = raw.resolve(strict=True)
    except (OSError, RuntimeError):
        raise RuntimeManifestError(f"{label}_does_not_exist") from None
    # Reject symlinked path components instead of silently following them.
    if resolved != raw:
        raise RuntimeManifestError(f"{label}_must_not_use_symlinks")
    return resolved


def _validate_file(path: Path, *, label: str, executable: bool = False) -> None:
    try:
        mode = path.lstat().st_mode
    except OSError:
        raise RuntimeManifestError(f"{label}_not_accessible") from None
    if not stat.S_ISREG(mode):
        raise RuntimeManifestError(f"{label}_must_be_regular_file")
    metadata = path.lstat()
    if metadata.st_nlink != 1:
        raise RuntimeManifestError(f"{label}_must_not_be_hard_linked")
    if mode & (stat.S_IWGRP | stat.S_IWOTH):
        raise RuntimeManifestError(f"{label}_must_not_be_group_or_world_writable")
    if executable and not os.access(path, os.X_OK):
        raise RuntimeManifestError(f"{label}_not_executable")


def _validate_directory(path: Path, *, label: str) -> None:
    try:
        metadata = path.lstat()
    except OSError:
        raise RuntimeManifestError(f"{label}_not_accessible") from None
    mode = metadata.st_mode
    if not stat.S_ISDIR(mode):
        raise RuntimeManifestError(f"{label}_must_be_real_directory")
    if path in _FORBIDDEN_DIRECTORY_MOUNTS:
        raise RuntimeManifestError(f"{label}_is_too_broad")
    if mode & (stat.S_IWGRP | stat.S_IWOTH):
        raise RuntimeManifestError(f"{label}_must_not_be_group_or_world_writable")


def _validate_directory_tree(path: Path, *, label: str) -> None:
    """Reject aliases and unsafe entries anywhere below an exposed directory."""
    _validate_directory(path, label=label)
    pending = [path]
    while pending:
        current = pending.pop()
        try:
            entries = tuple(current.iterdir())
        except OSError:
            raise RuntimeManifestError(f"{label}_contents_not_accessible") from None
        for entry in entries:
            try:
                metadata = entry.lstat()
            except OSError:
                raise RuntimeManifestError(f"{label}_entry_not_accessible") from None
            mode = metadata.st_mode
            if stat.S_ISLNK(mode):
                raise RuntimeManifestError("runtime_directory_contains_symlink")
            if stat.S_ISDIR(mode):
                if mode & (stat.S_IWGRP | stat.S_IWOTH):
                    raise RuntimeManifestError(
                        "runtime_directory_contains_writable_directory"
                    )
                pending.append(entry)
                continue
            if stat.S_ISREG(mode):
                if metadata.st_nlink != 1:
                    raise RuntimeManifestError(
                        "runtime_directory_contains_hard_linked_file"
                    )
                if mode & (stat.S_IWGRP | stat.S_IWOTH):
                    raise RuntimeManifestError(
                        "runtime_directory_contains_writable_file"
                    )
                continue
            raise RuntimeManifestError("runtime_directory_contains_special_file")


def _is_within(path: Path, directory: Path) -> bool:
    return path == directory or directory in path.parents


def _validate_destination(value: str | os.PathLike[str]) -> Path:
    """Validate a lexical in-sandbox destination without resolving it on host."""
    raw = os.fspath(value)
    if not isinstance(raw, str) or not raw.startswith("/") or "\x00" in raw:
        raise RuntimeManifestError("runtime_mount_destination_must_be_absolute")
    parts = raw.split("/")
    if ".." in parts or "." in parts:
        raise RuntimeManifestError("runtime_mount_destination_not_normalized")
    destination = Path(raw)
    if str(destination) != raw:
        raise RuntimeManifestError("runtime_mount_destination_not_normalized")
    if destination == Path("/"):
        raise RuntimeManifestError("runtime_mount_destination_is_root")
    if destination.parts[1] in {"proc", "dev", "tmp", "work"}:
        raise RuntimeManifestError("runtime_mount_destination_is_reserved")
    return destination


def _validate_mount_destinations(mounts: list[RuntimeMount]) -> None:
    destinations = [mount.destination for mount in mounts]
    if len(set(destinations)) != len(destinations):
        raise RuntimeManifestError("duplicate_runtime_mount_destination")
    for index, destination in enumerate(destinations):
        if any(_is_within(destination, other) for other in destinations[:index]):
            raise RuntimeManifestError("overlapping_runtime_mount_destinations")
        if any(_is_within(other, destination) for other in destinations[index + 1 :]):
            raise RuntimeManifestError("overlapping_runtime_mount_destinations")


def _validate_mount_boundaries(
    executable: Path,
    files: list[Path],
    directories: list[Path],
    alias_files: list[Path] = [],
) -> None:
    """Reject overlapping mounts that silently widen or shadow the closure."""
    all_files = [executable, *files, *alias_files]
    for index, directory in enumerate(directories):
        if any(_is_within(directory, other) for other in directories[:index]):
            raise RuntimeManifestError("overlapping_runtime_directories")
        if any(_is_within(other, directory) for other in directories[index + 1 :]):
            raise RuntimeManifestError("overlapping_runtime_directories")
        if any(_is_within(path, directory) for path in all_files):
            raise RuntimeManifestError("runtime_file_covered_by_directory_mount")


def build_runtime_manifest(
    executable: str | os.PathLike[str],
    *,
    required_files: Iterable[str | os.PathLike[str]] = (),
    required_directories: Iterable[str | os.PathLike[str]] = (),
    required_mounts: Iterable[RuntimeMount] = (),
) -> RuntimeManifest:
    """Validate an explicit runtime closure without discovering or executing tools.

    The caller (trusted packager/administrator) must enumerate the interpreter,
    dynamic loader, shared libraries, CA material and language runtime folders.
    This function intentionally does not run ldd, inspect arbitrary binaries,
    infer dependencies, or mount broad system directories. Any missing or
    ambiguous entry fails closed.
    """
    executable_path = _canonical_path(executable, label="runtime_executable")
    _validate_file(executable_path, label="runtime_executable", executable=True)

    file_paths = [_canonical_path(item, label="runtime_file") for item in required_files]
    directory_paths = [
        _canonical_path(item, label="runtime_directory")
        for item in required_directories
    ]
    alias_mounts: list[RuntimeMount] = []
    for item in required_mounts:
        if not isinstance(item, RuntimeMount):
            raise RuntimeManifestError("runtime_mount_invalid")
        if item.is_directory:
            raise RuntimeManifestError("runtime_directory_alias_not_supported")
        source = _canonical_path(item.source, label="runtime_mount_source")
        destination = _validate_destination(item.destination)
        if source == destination:
            raise RuntimeManifestError("runtime_mount_alias_must_change_destination")
        _validate_file(source, label="runtime_mount_source")
        alias_mounts.append(RuntimeMount(source, destination, False))

    if executable_path in file_paths or executable_path in directory_paths:
        raise RuntimeManifestError("runtime_executable_must_not_be_duplicated")
    if len(set(file_paths)) != len(file_paths):
        raise RuntimeManifestError("duplicate_runtime_file")
    if len(set(directory_paths)) != len(directory_paths):
        raise RuntimeManifestError("duplicate_runtime_directory")
    if set(file_paths) & set(directory_paths):
        raise RuntimeManifestError("runtime_path_type_conflict")
    alias_sources = [mount.source for mount in alias_mounts]
    if len(set(alias_sources)) != len(alias_sources) or set(alias_sources) & (
        set(file_paths) | set(directory_paths) | {executable_path}
    ):
        raise RuntimeManifestError("duplicate_runtime_mount_source")

    for path in file_paths:
        _validate_file(path, label="runtime_file")
    for path in directory_paths:
        _validate_directory_tree(path, label="runtime_directory")

    _validate_mount_boundaries(
        executable_path,
        file_paths,
        directory_paths,
        alias_sources,
    )

    mounts = [
        RuntimeMount(executable_path, executable_path, False),
        *(RuntimeMount(path, path, False) for path in sorted(file_paths)),
        *sorted(alias_mounts, key=lambda mount: (str(mount.destination), str(mount.source))),
        *(RuntimeMount(path, path, True) for path in sorted(directory_paths)),
    ]
    _validate_mount_destinations(mounts)
    return RuntimeManifest(executable_path, tuple(mounts))


def revalidate_runtime_manifest(manifest: RuntimeManifest) -> RuntimeManifest:
    """Reinspect every declared source immediately before sandbox construction.

    The manifest is data, not an authorization token: caller-constructed or
    stale instances are rebuilt from their explicit entries and must match the
    canonical validated representation exactly.
    """
    if not isinstance(manifest, RuntimeManifest):
        raise RuntimeManifestError("runtime_manifest_required")
    if not isinstance(manifest.mounts, tuple) or not manifest.mounts:
        raise RuntimeManifestError("runtime_manifest_mounts_invalid")
    files: list[Path] = []
    directories: list[Path] = []
    aliases: list[RuntimeMount] = []
    for mount in manifest.mounts:
        if not isinstance(mount, RuntimeMount):
            raise RuntimeManifestError("runtime_manifest_mount_invalid")
        if not isinstance(mount.is_directory, bool):
            raise RuntimeManifestError("runtime_manifest_mount_type_invalid")
        if mount.source == manifest.executable:
            if mount.is_directory or mount.destination != mount.source:
                raise RuntimeManifestError("runtime_executable_mount_type_invalid")
            continue
        if mount.is_directory:
            if mount.destination != mount.source:
                raise RuntimeManifestError("runtime_directory_alias_not_supported")
            directories.append(mount.source)
        elif mount.source == mount.destination:
            files.append(mount.source)
        else:
            aliases.append(mount)
    rebuilt = build_runtime_manifest(
        manifest.executable,
        required_files=files,
        required_directories=directories,
        required_mounts=aliases,
    )
    if rebuilt != manifest:
        raise RuntimeManifestError("runtime_manifest_not_canonical")
    return rebuilt
