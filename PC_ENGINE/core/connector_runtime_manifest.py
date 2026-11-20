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
    if executable and not os.access(path, os.X_OK):
        raise RuntimeManifestError(f"{label}_not_executable")


def _validate_directory(path: Path, *, label: str) -> None:
    try:
        mode = path.lstat().st_mode
    except OSError:
        raise RuntimeManifestError(f"{label}_not_accessible") from None
    if not stat.S_ISDIR(mode):
        raise RuntimeManifestError(f"{label}_must_be_real_directory")
    if path in _FORBIDDEN_DIRECTORY_MOUNTS:
        raise RuntimeManifestError(f"{label}_is_too_broad")
    # Reject a directory that contains a forbidden root. This catches broad
    # ancestors such as /usr/local's parent /usr before any mount is assembled.
    if any(forbidden in path.parents for forbidden in _FORBIDDEN_DIRECTORY_MOUNTS):
        raise RuntimeManifestError(f"{label}_is_inside_forbidden_root")


def build_runtime_manifest(
    executable: str | os.PathLike[str],
    *,
    required_files: Iterable[str | os.PathLike[str]] = (),
    required_directories: Iterable[str | os.PathLike[str]] = (),
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

    if executable_path in file_paths or executable_path in directory_paths:
        raise RuntimeManifestError("runtime_executable_must_not_be_duplicated")
    if len(set(file_paths)) != len(file_paths):
        raise RuntimeManifestError("duplicate_runtime_file")
    if len(set(directory_paths)) != len(directory_paths):
        raise RuntimeManifestError("duplicate_runtime_directory")
    if set(file_paths) & set(directory_paths):
        raise RuntimeManifestError("runtime_path_type_conflict")

    for path in file_paths:
        _validate_file(path, label="runtime_file")
    for path in directory_paths:
        _validate_directory(path, label="runtime_directory")

    mounts = [
        RuntimeMount(executable_path, executable_path, False),
        *(RuntimeMount(path, path, False) for path in sorted(file_paths)),
        *(RuntimeMount(path, path, True) for path in sorted(directory_paths)),
    ]
    return RuntimeManifest(executable_path, tuple(mounts))
