from __future__ import annotations

import os
import shutil
import stat
import sys
from pathlib import Path
from typing import Sequence

from PC_ENGINE.core.connector_runtime_manifest import (
    RuntimeManifest,
    RuntimeManifestError,
    revalidate_runtime_manifest,
)


class SandboxUnavailable(RuntimeError):
    """Raised when the required Linux sandbox cannot be positively verified."""


_SYSTEM_READ_ONLY_DIRS = ("/usr", "/lib", "/lib64", "/bin", "/sbin")
_SYSTEM_READ_ONLY_FILES = ("/etc/ld.so.cache",)
_SYSTEM_CERT_DIR = "/etc/ssl/certs"
_SENSITIVE_ROOTS = tuple(
    Path(item)
    for item in (
        "/home",
        "/root",
        "/etc",
        "/var",
        "/run",
        "/proc",
        "/sys",
        "/dev",
        "/tmp",
        "/mnt",
        "/media",
    )
)
_DEFAULT_TMP_BYTES = 16 * 1024 * 1024
_DEFAULT_WORK_BYTES = 64 * 1024 * 1024
_MAX_TMPFS_BYTES = 256 * 1024 * 1024
_MASKED_SYSTEM_PATHS = ("/usr/local",)


def _real_directory(value: str | os.PathLike[str], *, label: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        raise ValueError(f"{label}_must_be_absolute")
    try:
        resolved = path.resolve(strict=True)
    except (OSError, RuntimeError):
        raise ValueError(f"{label}_does_not_exist") from None
    if not resolved.is_dir():
        raise ValueError(f"{label}_must_be_directory")
    return resolved


def _is_within(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def _system_runtime_roots() -> tuple[list[tuple[Path, Path]], list[Path]]:
    mounts: list[tuple[Path, Path]] = []
    roots: list[Path] = []
    for item in _SYSTEM_READ_ONLY_DIRS:
        source_path = Path(item)
        try:
            resolved = source_path.resolve(strict=True)
        except (OSError, RuntimeError):
            continue
        if not source_path.is_dir() or not resolved.is_dir():
            continue
        # Preserve loader/command aliases such as /lib64 and /bin inside the
        # sandbox even on merged-/usr hosts where their sources resolve under /usr.
        mounts.append((resolved, source_path))
        if resolved not in roots:
            roots.append(resolved)
    return mounts, roots


def _validate_tmpfs_size(value: int, *, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{label}_must_be_integer")
    if value <= 0 or value > _MAX_TMPFS_BYTES:
        raise ValueError(f"{label}_out_of_bounds")
    return value


def _validate_runtime_root(root: Path) -> None:
    for sensitive in _SENSITIVE_ROOTS:
        if root == sensitive or root in sensitive.parents:
            raise ValueError("sandbox_runtime_root_overlaps_sensitive_path")
        if sensitive in root.parents:
            raise ValueError("sandbox_runtime_root_overlaps_sensitive_path")


def build_linux_bwrap_command(
    command: Sequence[str],
    *,
    runtime_roots: Sequence[str | os.PathLike[str]] = (),
    tmp_size_bytes: int = _DEFAULT_TMP_BYTES,
    work_size_bytes: int = _DEFAULT_WORK_BYTES,
    bwrap_path: str | os.PathLike[str] | None = None,
    runtime_manifest: RuntimeManifest | None = None,
) -> list[str]:
    """Build a fail-closed Linux Bubblewrap command with bounded writable tmpfs.

    This function only constructs argv; it does not launch or attest a sandbox.
    Callers must execute argv without a shell, keep the runtime roots immutable
    for the duration of the launch, and treat setup or enforcement failures as
    a hard denial. The sandbox receives no host home, VST data, Vault, secrets,
    host temporary directory, or network namespace.

    Writable /tmp and /work are private tmpfs mounts with explicit size caps.
    Results must leave the sandbox through the bounded worker IPC protocol;
    no host scratch directory is bind-mounted into an untrusted process.
    """
    if sys.platform != "linux":
        raise SandboxUnavailable("linux_sandbox_platform_required")
    if isinstance(command, (str, bytes)) or not isinstance(command, Sequence):
        raise ValueError("sandbox_command_must_be_sequence")
    if not command or any(
        not isinstance(part, str) or not part or "\x00" in part
        for part in command
    ):
        raise ValueError("sandbox_command_required")
    if isinstance(runtime_roots, (str, bytes, os.PathLike)) or not isinstance(
        runtime_roots, Sequence
    ):
        raise ValueError("sandbox_runtime_roots_must_be_sequence")

    tmp_size = _validate_tmpfs_size(tmp_size_bytes, label="sandbox_tmp_size")
    work_size = _validate_tmpfs_size(work_size_bytes, label="sandbox_work_size")

    binary = bwrap_path or shutil.which("bwrap")
    if not binary:
        raise SandboxUnavailable("linux_bwrap_unavailable")
    try:
        binary_path = Path(binary).resolve(strict=True)
    except (OSError, RuntimeError):
        raise SandboxUnavailable("linux_bwrap_not_found") from None
    if not binary_path.is_file() or not os.access(binary_path, os.X_OK):
        raise SandboxUnavailable("linux_bwrap_not_executable")

    roots = [
        _real_directory(root, label="sandbox_runtime_root")
        for root in runtime_roots
    ]
    if len(set(roots)) != len(roots):
        raise ValueError("duplicate_sandbox_runtime_root")
    for root in roots:
        _validate_runtime_root(root)

    if runtime_manifest is not None and roots:
        raise ValueError("sandbox_manifest_and_legacy_roots_are_mutually_exclusive")

    if runtime_manifest is not None:
        try:
            validated_manifest = revalidate_runtime_manifest(runtime_manifest)
        except RuntimeManifestError as exc:
            raise ValueError(str(exc)) from None
        if Path(command[0]) != validated_manifest.executable:
            raise ValueError("sandbox_command_must_use_manifest_executable")
        executable_real = validated_manifest.executable
        explicit_mounts = validated_manifest.mounts
        system_mounts: list[tuple[Path, Path]] = []
        system_roots: list[Path] = []
        allowed_exec_roots = [executable_real.parent]
    else:
        validated_manifest = None
        system_mounts, system_roots = _system_runtime_roots()
        allowed_exec_roots = [*system_roots, *roots]
    executable = Path(command[0])
    if not executable.is_absolute():
        raise ValueError("sandbox_executable_must_be_absolute")
    if validated_manifest is None:
        try:
            executable_real = executable.resolve(strict=True)
        except (OSError, RuntimeError):
            raise ValueError("sandbox_executable_not_found") from None
        if not executable_real.is_file() or not os.access(executable_real, os.X_OK):
            raise ValueError("sandbox_executable_not_executable")
        if not any(_is_within(executable_real, root) for root in allowed_exec_roots):
            raise ValueError("sandbox_executable_outside_runtime_roots")

    normalized_command = [str(executable_real), *command[1:]]
    argv = [
        str(binary_path),
        "--die-with-parent",
        "--new-session",
        "--unshare-user",
        "--unshare-pid",
        "--unshare-ipc",
        "--unshare-uts",
        "--unshare-net",
        "--clearenv",
    ]
    if validated_manifest is not None:
        # Build only empty destination parents, from shallow to deep. No host
        # root, /usr, /lib, /bin, /etc or other implicit runtime tree is mounted.
        destinations = [mount.destination for mount in explicit_mounts]
        parent_directories: set[Path] = set()
        reserved = {Path("/"), Path("/proc"), Path("/dev"), Path("/tmp"), Path("/work")}
        for destination in destinations:
            for parent in destination.parents:
                if parent in reserved:
                    break
                parent_directories.add(parent)
        for directory in sorted(parent_directories, key=lambda item: (len(item.parts), str(item))):
            argv.extend(["--dir", str(directory)])
        for mount in explicit_mounts:
            argv.extend(["--ro-bind", str(mount.source), str(mount.destination)])
    else:
        for source, destination in system_mounts:
            argv.extend(["--ro-bind", str(source), str(destination)])
    if validated_manifest is None:
        for file_path in _SYSTEM_READ_ONLY_FILES:
            try:
                path = Path(file_path).resolve(strict=True)
            except (OSError, RuntimeError):
                continue
            if path.is_file():
                argv.extend(["--ro-bind", str(path), str(path)])

    # The legacy compatibility path masks host-local content after broad mounts.
    # Mask the complete host-local subtree, not only selected subdirectories,
    # so additional /usr/local content cannot be exposed through the broad mount.
    for sensitive_mount in (() if validated_manifest is not None else _MASKED_SYSTEM_PATHS):
        sensitive_path = Path(sensitive_mount)
        try:
            sensitive_mode = sensitive_path.lstat().st_mode
        except FileNotFoundError:
            continue
        except OSError:
            raise SandboxUnavailable("linux_sensitive_mount_unavailable") from None
        if stat.S_ISLNK(sensitive_mode) or not stat.S_ISDIR(sensitive_mode):
            raise ValueError("sandbox_sensitive_mount_must_be_real_directory")
        argv.extend(["--perms", "0700", "--tmpfs", sensitive_mount])

    if validated_manifest is None:
        try:
            certs = Path(_SYSTEM_CERT_DIR).resolve(strict=True)
        except (OSError, RuntimeError):
            certs = None
        if certs is not None and certs.is_dir() and not any(
            _is_within(certs, root) for root in system_roots
        ):
            argv.extend(["--ro-bind", str(certs), str(certs)])

        for root in roots:
            if any(_is_within(root, system) for system in system_roots):
                continue
            argv.extend(["--ro-bind", str(root), str(root)])

    argv.extend(
        [
            "--proc", "/proc",
            "--dev", "/dev",
            "--size", str(tmp_size),
            "--perms", "0700",
            "--tmpfs", "/tmp",
            "--size", str(work_size),
            "--perms", "0700",
            "--tmpfs", "/work",
            "--chdir", "/work",
            "--setenv", "PATH", ("/usr/bin" if validated_manifest is None else "/work/bin"),
            "--setenv", "HOME", "/work",
            "--setenv", "TMPDIR", "/tmp",
            "--",
            *normalized_command,
        ]
    )
    return argv
