from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path

import pytest

from PC_ENGINE.core.connector_runtime_manifest import build_runtime_manifest
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
    if Path("/usr/local").is_dir() and not Path("/usr/local").is_symlink():
        mask_index = argv.index("/usr/local")
        assert argv[mask_index - 3 : mask_index + 1] == [
            "--perms", "0700", "--tmpfs", "/usr/local"
        ]
        assert argv.index("--ro-bind") < mask_index
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
        "if os.path.isdir('/usr/local') and os.listdir('/usr/local'):\n"
        "    raise SystemExit('HOST_LOCAL_TREE_VISIBLE')\n"
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


def test_manifest_backed_builder_mounts_only_explicit_runtime_entries(tmp_path):
    executable = tmp_path / "runtime" / "python"
    executable.parent.mkdir(parents=True)
    executable.write_text("runtime", encoding="utf-8")
    executable.chmod(0o555)
    library = tmp_path / "runtime" / "libpython.so"
    library.write_text("library", encoding="utf-8")
    library.chmod(0o444)
    stdlib = tmp_path / "runtime" / "stdlib"
    stdlib.mkdir()
    (stdlib / "module.py").write_text("value = 1", encoding="utf-8")
    (stdlib / "module.py").chmod(0o444)
    stdlib.chmod(0o555)
    manifest = build_runtime_manifest(
        executable,
        required_files=[library],
        required_directories=[stdlib],
    )

    argv = build_linux_bwrap_command(
        [str(executable), "-c", "pass"],
        runtime_manifest=manifest,
        python_home=str(tmp_path / "runtime"),
        bwrap_path=_fake_bwrap(tmp_path / "bwrap"),
    )

    assert "--unshare-net" in argv
    assert "--ro-bind" in argv
    assert argv.index("--tmpfs") < argv.index("--ro-bind")
    assert str(executable) in argv
    assert str(library) in argv
    assert str(stdlib) in argv
    assert "/usr" not in argv
    assert "/lib" not in argv
    assert "/bin" not in argv
    assert "/etc/ld.so.cache" not in argv
    assert "/usr/bin" not in argv
    assert argv[argv.index("--setenv") + 2] == "/work/bin"
    setenv = [
        argv[index:index + 3]
        for index, value in enumerate(argv)
        if value == "--setenv"
    ]
    assert ["--setenv", "PYTHONHOME", str(tmp_path / "runtime")] in setenv
    assert ["--setenv", "PYTHONNOUSERSITE", "1"] in setenv
    assert ["--setenv", "PYTHONDONTWRITEBYTECODE", "1"] in setenv
    assert ["--setenv", "PYTHONSAFEPATH", "1"] in setenv


def test_manifest_backed_builder_rejects_command_executable_mismatch(tmp_path):
    executable = tmp_path / "python"
    executable.write_text("runtime", encoding="utf-8")
    executable.chmod(0o555)
    other = tmp_path / "other-python"
    other.write_text("other", encoding="utf-8")
    other.chmod(0o555)
    manifest = build_runtime_manifest(executable)

    with pytest.raises(ValueError, match="sandbox_command_must_use_manifest_executable"):
        build_linux_bwrap_command(
            [str(other)],
            runtime_manifest=manifest,
            bwrap_path=_fake_bwrap(tmp_path / "bwrap"),
        )


def test_manifest_backed_builder_rejects_legacy_runtime_roots(tmp_path):
    executable = tmp_path / "python"
    executable.write_text("runtime", encoding="utf-8")
    executable.chmod(0o555)
    manifest = build_runtime_manifest(executable)

    with pytest.raises(ValueError, match="sandbox_manifest_and_legacy_roots_are_mutually_exclusive"):
        build_linux_bwrap_command(
            [str(executable)],
            runtime_roots=[tmp_path],
            runtime_manifest=manifest,
            bwrap_path=_fake_bwrap(tmp_path / "bwrap"),
        )


def test_manifest_backed_builder_revalidates_sources_before_command_construction(tmp_path):
    executable = tmp_path / "python"
    executable.write_text("runtime", encoding="utf-8")
    executable.chmod(0o555)
    library = tmp_path / "libpython.so"
    library.write_text("library", encoding="utf-8")
    library.chmod(0o444)
    manifest = build_runtime_manifest(executable, required_files=[library])
    library.unlink()

    with pytest.raises(ValueError, match="runtime_file_does_not_exist"):
        build_linux_bwrap_command(
            [str(executable)],
            runtime_manifest=manifest,
            bwrap_path=_fake_bwrap(tmp_path / "bwrap"),
        )


def test_manifest_backed_bwrap_hides_undeclared_host_files_and_tools(tmp_path):
    if os.environ.get("VST_RUN_BWRAP_INTEGRATION") != "1":
        pytest.skip("Real Bubblewrap execution is reserved for the dedicated Linux CI workflow")
    bwrap = shutil.which("bwrap")
    compiler = shutil.which("cc")
    if not bwrap or not compiler:
        pytest.fail("Dedicated Linux CI workflow must install Bubblewrap and cc")

    executable = tmp_path / "manifest-runtime-check"
    host_marker = tmp_path / "host-only-marker"
    host_marker.write_text("must-not-be-visible", encoding="utf-8")
    marker = str(host_marker)
    assembly = tmp_path / "runtime-check.s"
    assembly.write_text(
        ".section .rodata\n"
        f'host_tool: .asciz "/usr/bin/id"\n'
        f'host_config: .asciz "/etc/passwd"\n'
        f'host_marker: .asciz "{marker}"\n'
        'success: .ascii "manifest-runtime-only"\n'
        ".text\n"
        ".global _start\n"
        "_start:\n"
        "  mov $21, %rax\n"
        "  lea host_tool(%rip), %rdi\n"
        "  xor %rsi, %rsi\n"
        "  syscall\n"
        "  cmp $-2, %rax\n"
        "  jne fail\n"
        "  mov $21, %rax\n"
        "  lea host_config(%rip), %rdi\n"
        "  xor %rsi, %rsi\n"
        "  syscall\n"
        "  cmp $-2, %rax\n"
        "  jne fail\n"
        "  mov $21, %rax\n"
        "  lea host_marker(%rip), %rdi\n"
        "  xor %rsi, %rsi\n"
        "  syscall\n"
        "  cmp $-2, %rax\n"
        "  jne fail\n"
        "  mov $1, %rax\n"
        "  mov $1, %rdi\n"
        "  lea success(%rip), %rsi\n"
        "  mov $21, %rdx\n"
        "  syscall\n"
        "  mov $60, %rax\n"
        "  xor %rdi, %rdi\n"
        "  syscall\n"
        "fail:\n"
        "  mov $60, %rax\n"
        "  mov $42, %rdi\n"
        "  syscall\n",
        encoding="utf-8",
    )
    compiled = subprocess.run(
        [compiler, "-nostdlib", "-static", "-no-pie", "-Wl,-e,_start", "-o", str(executable), str(assembly)],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert compiled.returncode == 0, compiled.stderr[-2000:]
    executable.chmod(0o555)
    manifest = build_runtime_manifest(executable)
    argv = build_linux_bwrap_command(
        [str(executable)],
        runtime_manifest=manifest,
        bwrap_path=bwrap,
    )
    result = subprocess.run(argv, capture_output=True, text=True, timeout=20, check=False)
    assert result.returncode == 0, (
        f"Manifest-backed Bubblewrap failed with exit {result.returncode}: "
        f"{result.stderr[-2000:]}"
    )
    assert "manifest-runtime-only" in result.stdout
