from __future__ import annotations

import shutil
import socket
import subprocess
import sys
from pathlib import Path

import pytest

from PC_ENGINE.core.connector_worker_sandbox import (
    SandboxUnavailable,
    build_linux_bwrap_command,
)

pytestmark = pytest.mark.skipif(
    sys.platform != "linux",
    reason="Bubblewrap command construction is Linux-specific",
)


def _fake_bwrap(path: Path) -> Path:
    path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    path.chmod(0o700)
    return path


def test_linux_sandbox_command_denies_network_and_bounds_writable_tmpfs(tmp_path):
    argv = build_linux_bwrap_command(
        ["/usr/bin/python3", "--version"],
        bwrap_path=_fake_bwrap(tmp_path / "bwrap"),
    )

    assert "--unshare-net" in argv
    assert "--unshare-user" in argv
    assert "--clearenv" in argv
    assert "--bind" not in argv
    assert argv[-2:] == [str(Path("/usr/bin/python3").resolve()), "--version"]

    tmpfs_indices = [index for index, item in enumerate(argv) if item == "--tmpfs"]
    assert len(tmpfs_indices) == 2
    expected = [
        ["--size", str(16 * 1024 * 1024), "--perms", "0700", "--tmpfs", "/tmp"],
        ["--size", str(64 * 1024 * 1024), "--perms", "0700", "--tmpfs", "/work"],
    ]
    for index, values in zip(tmpfs_indices, expected):
        assert argv[index - 4 : index + 2] == values


def test_linux_sandbox_rejects_executable_outside_declared_roots(tmp_path):
    outside = tmp_path / "outside"
    outside.write_text("not executable", encoding="utf-8")
    outside.chmod(0o700)

    with pytest.raises(ValueError, match="sandbox_executable_outside_runtime_roots"):
        build_linux_bwrap_command(
            [str(outside)],
            bwrap_path=_fake_bwrap(tmp_path / "bwrap"),
        )


def test_linux_sandbox_rejects_sensitive_or_broad_runtime_roots(tmp_path):
    with pytest.raises(ValueError, match="sandbox_runtime_root_overlaps_sensitive_path"):
        build_linux_bwrap_command(
            ["/usr/bin/python3"],
            runtime_roots=[Path("/tmp")],
            bwrap_path=_fake_bwrap(tmp_path / "bwrap"),
        )


@pytest.mark.parametrize(
    ("value", "message"),
    [
        (0, "sandbox_work_size_out_of_bounds"),
        (-1, "sandbox_work_size_out_of_bounds"),
        (257 * 1024 * 1024, "sandbox_work_size_out_of_bounds"),
        (True, "sandbox_work_size_must_be_integer"),
    ],
)
def test_linux_sandbox_rejects_invalid_work_tmpfs_size(tmp_path, value, message):
    with pytest.raises(ValueError, match=message):
        build_linux_bwrap_command(
            ["/usr/bin/python3"],
            work_size_bytes=value,
            bwrap_path=_fake_bwrap(tmp_path / "bwrap"),
        )


def test_linux_sandbox_fails_closed_when_bwrap_is_missing(monkeypatch):
    monkeypatch.setattr(
        "PC_ENGINE.core.connector_worker_sandbox.shutil.which",
        lambda _: None,
    )

    with pytest.raises(SandboxUnavailable, match="linux_bwrap_unavailable"):
        build_linux_bwrap_command(["/usr/bin/python3"])


def test_linux_sandbox_executes_and_denies_host_file_and_loopback_network(tmp_path):
    bwrap = shutil.which("bwrap")
    if not bwrap:
        pytest.skip("Bubblewrap is installed by the dedicated Linux CI workflow")

    host_marker = tmp_path / "host-only-marker.txt"
    host_marker.write_text("not-mounted-into-sandbox", encoding="utf-8")

    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    port = listener.getsockname()[1]
    work_limit = 64 * 1024 * 1024

    script = (
        "import os, socket, sys\n"
        "marker, port, work_limit = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])\n"
        "try:\n"
        "    open(marker, 'rb').read()\n"
        "except FileNotFoundError:\n"
        "    pass\n"
        "else:\n"
        "    raise SystemExit('HOST_FILE_VISIBLE')\n"
        "client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)\n"
        "client.settimeout(1.0)\n"
        "try:\n"
        "    client.connect(('127.0.0.1', port))\n"
        "except OSError:\n"
        "    pass\n"
        "else:\n"
        "    raise SystemExit('HOST_NETWORK_VISIBLE')\n"
        "finally:\n"
        "    client.close()\n"
        "stat = os.statvfs('/work')\n"
        "capacity = stat.f_frsize * stat.f_blocks\n"
        "if capacity > work_limit + 4096:\n"
        "    raise SystemExit('WORK_TMPFS_LIMIT_NOT_ENFORCED')\n"
        "print('filesystem-network-and-tmpfs-boundaries-enforced')\n"
    )
    try:
        argv = build_linux_bwrap_command(
            [
                sys.executable,
                "-c",
                script,
                str(host_marker),
                str(port),
                str(work_limit),
            ],
            runtime_roots=[Path(sys.prefix)],
            bwrap_path=bwrap,
            work_size_bytes=work_limit,
        )
        result = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    finally:
        listener.close()

    assert result.returncode == 0, (
        f"Bubblewrap enforcement failed with exit {result.returncode}: "
        f"{result.stderr[-2000:]}"
    )
    assert "filesystem-network-and-tmpfs-boundaries-enforced" in result.stdout
