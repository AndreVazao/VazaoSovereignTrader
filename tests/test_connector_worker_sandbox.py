from __future__ import annotations

import os
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
    assert "/lib64" in argv
    assert "/bin" in argv
    assert argv[-2:] == [str(Path("/usr/bin/python3").resolve()), "--version"]

    tmpfs_indices = [
        index
        for index, item in enumerate(argv)
        if item == "--tmpfs" and argv[index + 1] in ("/tmp", "/work")
    ]
    assert len(tmpfs_indices) == 2
    for sensitive_mount in ("/usr/local/etc", "/usr/local/var", "/usr/local/bin"):
        if Path(sensitive_mount).is_dir() and not Path(sensitive_mount).is_symlink():
            assert sensitive_mount in argv
    expected = [
        ["--size", str(16 * 1024 * 1024), "--perms", "0700", "--tmpfs", "/tmp"],
        ["--size", str(64 * 1024 * 1024), "--perms", "0700", "--tmpfs", "/work"],
    ]
    for index, values in zip(tmpfs_indices, expected):
        assert argv[index - 4 : index + 2] == values



def test_linux_sandbox_fails_closed_for_symlinked_sensitive_mountpoint(tmp_path, monkeypatch):
    runtime_link = tmp_path / "runtime"
    runtime_link.mkdir()
    sensitive_target = tmp_path / "sensitive-target"
    sensitive_target.mkdir()
    sensitive_link = tmp_path / "sensitive-link"
    sensitive_link.symlink_to(sensitive_target, target_is_directory=True)
    monkeypatch.setattr(
        "PC_ENGINE.core.connector_worker_sandbox._SENSITIVE_ROOTS",
        (),
    )
    monkeypatch.setattr(
        "PC_ENGINE.core.connector_worker_sandbox._MASKED_SYSTEM_PATHS",
        (str(sensitive_link),),
    )

    with pytest.raises(
        ValueError,
        match="sandbox_sensitive_mount_must_be_real_directory",
    ):
        build_linux_bwrap_command(
            ["/usr/bin/python3"],
            runtime_roots=[str(runtime_link)],
            bwrap_path=_fake_bwrap(tmp_path / "bwrap"),
        )


def test_linux_sandbox_fails_closed_for_non_directory_sensitive_mountpoint(tmp_path, monkeypatch):
    runtime_link = tmp_path / "runtime"
    runtime_link.mkdir()
    sensitive_file = tmp_path / "sensitive-file"
    sensitive_file.write_text("host-state", encoding="utf-8")
    monkeypatch.setattr(
        "PC_ENGINE.core.connector_worker_sandbox._SENSITIVE_ROOTS",
        (),
    )
    monkeypatch.setattr(
        "PC_ENGINE.core.connector_worker_sandbox._MASKED_SYSTEM_PATHS",
        (str(sensitive_file),),
    )

    with pytest.raises(
        ValueError,
        match="sandbox_sensitive_mount_must_be_real_directory",
    ):
        build_linux_bwrap_command(
            ["/usr/bin/python3"],
            runtime_roots=[str(runtime_link)],
            bwrap_path=_fake_bwrap(tmp_path / "bwrap"),
        )

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


def test_linux_sandbox_rejects_filesystem_root_runtime_mount(tmp_path):
    with pytest.raises(ValueError, match="sandbox_runtime_root_overlaps_sensitive_path"):
        build_linux_bwrap_command(
            ["/usr/bin/python3"],
            runtime_roots=[Path("/")],
            bwrap_path=_fake_bwrap(tmp_path / "bwrap"),
        )


def test_linux_sandbox_rejects_symlinked_runtime_root_into_sensitive_path(tmp_path):
    runtime_link = tmp_path / "runtime-link"
    runtime_link.symlink_to("/tmp", target_is_directory=True)

    with pytest.raises(ValueError, match="sandbox_runtime_root_overlaps_sensitive_path"):
        build_linux_bwrap_command(
            ["/usr/bin/python3"],
            runtime_roots=[runtime_link],
            bwrap_path=_fake_bwrap(tmp_path / "bwrap"),
        )


def test_linux_sandbox_rejects_symlinked_executable_outside_runtime_roots(tmp_path):
    outside = tmp_path / "outside-executable"
    outside.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    outside.chmod(0o700)
    executable_link = tmp_path / "python"
    executable_link.symlink_to(outside)

    with pytest.raises(ValueError, match="sandbox_executable_outside_runtime_roots"):
        build_linux_bwrap_command(
            [str(executable_link)],
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


def test_linux_sandbox_enforces_filesystem_network_environment_and_tmpfs_boundaries(tmp_path):
    if os.environ.get("VST_RUN_BWRAP_INTEGRATION") != "1":
        pytest.skip("Real Bubblewrap execution is reserved for the dedicated Linux CI workflow")
    bwrap = shutil.which("bwrap")
    if not bwrap:
        pytest.fail("Dedicated Linux CI workflow did not install Bubblewrap")

    host_marker = tmp_path / "host-only-marker.txt"
    host_marker.write_text("not-mounted-into-sandbox", encoding="utf-8")

    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    port = listener.getsockname()[1]
    tmp_limit = 16 * 1024 * 1024
    work_limit = 64 * 1024 * 1024

    script = (
        "import os, socket, sys\n"
        "marker, port, tmp_limit, work_limit = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])\n"
        "if 'VST_SANDBOX_TEST_INHERITED_MARKER' in os.environ:\n"
        "    raise SystemExit('HOST_ENVIRONMENT_VISIBLE')\n"
        "if os.environ.get('HOME') != '/work' or os.environ.get('TMPDIR') != '/tmp':\n"
        "    raise SystemExit('SANDBOX_ENVIRONMENT_NOT_NORMALIZED')\n"
        "if os.environ.get('PATH') != '/usr/bin':\n"
        "    raise SystemExit('SANDBOX_PATH_NOT_MINIMAL')\n"
        "if os.path.isdir('/usr/local/bin') and os.listdir('/usr/local/bin'):\n"
        "    raise SystemExit('HOST_LOCAL_EXECUTABLES_VISIBLE')\n"
        "try:\n"
        "    open(marker, 'rb').read()\n"
        "except FileNotFoundError:\n"
        "    pass\n"
        "else:\n"
        "    raise SystemExit('HOST_FILE_VISIBLE')\n"
        "if os.path.exists('/etc/passwd'):\n"
        "    raise SystemExit('HOST_ETC_VISIBLE')\n"
        "for path in ('/usr/local/etc', '/usr/local/var', '/usr/local/bin'):\n"
        "    if os.path.isdir(path) and os.listdir(path):\n"
        "        raise SystemExit('HOST_LOCAL_CONFIG_OR_STATE_VISIBLE:' + path)\n"
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
        "for path, limit, label in (('/tmp', tmp_limit, 'TMP'), ('/work', work_limit, 'WORK')):\n"
        "    stat = os.statvfs(path)\n"
        "    capacity = stat.f_frsize * stat.f_blocks\n"
        "    if capacity > limit + 4096:\n"
        "        raise SystemExit(label + '_TMPFS_LIMIT_NOT_ENFORCED')\n"
        "print('filesystem-network-environment-and-tmpfs-boundaries-enforced')\n"
    )
    try:
        argv = build_linux_bwrap_command(
            [
                "/usr/bin/python3",
                "-c",
                script,
                str(host_marker),
                str(port),
                str(tmp_limit),
                str(work_limit),
            ],
            bwrap_path=bwrap,
            tmp_size_bytes=tmp_limit,
            work_size_bytes=work_limit,
        )
        result = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
            env={
                **os.environ,
                "VST_SANDBOX_TEST_INHERITED_MARKER": "host-only",
            },
        )
    finally:
        listener.close()

    assert result.returncode == 0, (
        f"Bubblewrap enforcement failed with exit {result.returncode}: "
        f"{result.stderr[-2000:]}"
    )
    assert "filesystem-network-environment-and-tmpfs-boundaries-enforced" in result.stdout
