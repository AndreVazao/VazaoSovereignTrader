from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import Sequence


class SandboxUnavailable(RuntimeError):
    """Raised when the required Linux sandbox cannot be positively verified."""


_SYSTEM_READ_ONLY_DIRS = ("/usr", "/lib", "/lib64")
_SYSTEM_READ_ONLY_FILES = ("/etc/ld.so.cache",)
_SYSTEM_CERT_DIR = "/etc/ssl/certs"


def _real_directory(value: str | os.PathLike[str], *, label: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        raise ValueError(f"{label}_must_be_absolute")
    try:
        resolved = path.resolve(strict=True)
    except OSError:
        raise ValueError(f"{label}_does_not_exist") from None
    if not resolved.is_dir():
        raise ValueError(f"{label}_must_be_directory")
    return resolved


def build_linux_bwrap_command(
    command: Sequence[str],
    *,
    runtime_roots: Sequence[str | os.PathLike[str]],
    scratch_dir: str | os.PathLike[str],
    bwrap_path: str | None = None,
) -> list[str]:
    """Build a deny-network, minimal-filesystem Bubblewrap invocation.

    This function only constructs argv; it does not launch or attest a sandbox.
    Callers must execute argv without a shell, provision a fresh private scratch
    directory, and pass only reviewed read-only runtime roots. The returned
    command has no network namespace, host home, VST data, or credential mounts.
    """
    if sys.platform != "linux":
        raise SandboxUnavailable("linux_sandbox_platform_required")
    if not command or any(not isinstance(part, str) or not part for part in command):
        raise ValueError("sandbox_command_required")
    executable = Path(command[0])
    if not executable.is_absolute():
        raise ValueError("sandbox_executable_must_be_absolute")

    binary = bwrap_path or shutil.which("bwrap")
    if not binary:
        raise SandboxUnavailable("linux_bwrap_unavailable")
    binary_path = Path(binary)
    if not binary_path.is_absolute() or not os.access(binary_path, os.X_OK):
        raise SandboxUnavailable("linux_bwrap_not_executable")

    scratch_input = Path(scratch_dir)
    if scratch_input.is_symlink():
        raise ValueError("sandbox_scratch_must_not_be_symlink")
    scratch = _real_directory(scratch_input, label="sandbox_scratch")
    try:
        mode = scratch.stat().st_mode & 0o777
    except OSError:
        raise ValueError("sandbox_scratch_unavailable") from None
    if mode & 0o077:
        raise ValueError("sandbox_scratch_permissions_too_open")

    roots = [_real_directory(root, label="sandbox_runtime_root") for root in runtime_roots]
    if not roots:
        raise ValueError("sandbox_runtime_roots_required")
    if len(set(roots)) != len(roots):
        raise ValueError("duplicate_sandbox_runtime_root")
    if Path("/") in roots:
        raise ValueError("sandbox_root_mount_forbidden")

    system_roots = [
        Path(item) for item in _SYSTEM_READ_ONLY_DIRS if Path(item).is_dir()
    ]
    allowed_exec_roots = [*system_roots, *roots]
    executable_real = executable.resolve(strict=True)
    if not executable.is_file() or not os.access(executable_real, os.X_OK):
        raise ValueError("sandbox_executable_not_executable")
    if not any(
        executable_real == root or root in executable_real.parents
        for root in allowed_exec_roots
    ):
        raise ValueError("sandbox_executable_outside_runtime_roots")

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
    for root in system_roots:
        argv.extend(["--ro-bind", str(root), str(root)])
    for file_path in _SYSTEM_READ_ONLY_FILES:
        path = Path(file_path)
        if path.is_file():
            argv.extend(["--ro-bind", str(path), str(path)])
    certs = Path(_SYSTEM_CERT_DIR)
    if certs.is_dir():
        argv.extend(["--ro-bind", str(certs), str(certs)])

    for root in roots:
        if any(root == system or system in root.parents for system in system_roots):
            continue
        argv.extend(["--ro-bind", str(root), str(root)])

    argv.extend(
        [
            "--proc", "/proc",
            "--dev", "/dev",
            "--tmpfs", "/tmp",
            "--bind", str(scratch), "/work",
            "--chdir", "/work",
            "--setenv", "PATH", "/usr/local/bin:/usr/bin",
            "--",
            *command,
        ]
    )
    return argv
