from __future__ import annotations

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


def _private_dir(path: Path) -> Path:
    path.mkdir()
    path.chmod(0o700)
    return path


def test_linux_sandbox_command_denies_network_and_does_not_mount_host_root(tmp_path):
    runtime = _private_dir(tmp_path / "runtime")
    scratch = _private_dir(tmp_path / "scratch")
    executable = runtime / "worker"
    executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    executable.chmod(0o700)
    bwrap = tmp_path / "bwrap"
    bwrap.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    bwrap.chmod(0o700)

    argv = build_linux_bwrap_command(
        [str(executable), "--probe"],
        runtime_roots=[str(runtime)],
        scratch_dir=str(scratch),
        bwrap_path=str(bwrap),
    )

    assert "--unshare-net" in argv
    assert "--clearenv" in argv
    assert "--tmpfs" in argv
    assert "/work" in argv
    assert "--bind" in argv
    assert not any(
        argv[index] == "--ro-bind" and argv[index + 1] == "/" and argv[index + 2] == "/"
        for index in range(len(argv) - 2)
    )
    assert argv[-2:] == [str(executable), "--probe"]


def test_linux_sandbox_rejects_executable_outside_declared_roots(tmp_path):
    runtime = _private_dir(tmp_path / "runtime")
    scratch = _private_dir(tmp_path / "scratch")
    outside = tmp_path / "outside"
    outside.write_text("not executable", encoding="utf-8")
    outside.chmod(0o700)
    bwrap = tmp_path / "bwrap"
    bwrap.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    bwrap.chmod(0o700)

    with pytest.raises(ValueError, match="sandbox_executable_outside_runtime_roots"):
        build_linux_bwrap_command(
            [str(outside)],
            runtime_roots=[str(runtime)],
            scratch_dir=str(scratch),
            bwrap_path=str(bwrap),
        )


def test_linux_sandbox_rejects_world_accessible_scratch(tmp_path):
    runtime = _private_dir(tmp_path / "runtime")
    scratch = tmp_path / "scratch"
    scratch.mkdir(mode=0o755)
    scratch.chmod(0o755)
    executable = runtime / "worker"
    executable.write_text("x", encoding="utf-8")
    executable.chmod(0o700)
    bwrap = tmp_path / "bwrap"
    bwrap.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    bwrap.chmod(0o700)

    with pytest.raises(ValueError, match="sandbox_scratch_permissions_too_open"):
        build_linux_bwrap_command(
            [str(executable)],
            runtime_roots=[str(runtime)],
            scratch_dir=str(scratch),
            bwrap_path=str(bwrap),
        )


def test_linux_sandbox_fails_closed_when_bwrap_is_missing(tmp_path, monkeypatch):
    runtime = _private_dir(tmp_path / "runtime")
    scratch = _private_dir(tmp_path / "scratch")
    executable = runtime / "worker"
    executable.write_text("x", encoding="utf-8")
    executable.chmod(0o700)
    monkeypatch.setattr(
        "PC_ENGINE.core.connector_worker_sandbox.shutil.which",
        lambda _: None,
    )

    with pytest.raises(SandboxUnavailable, match="linux_bwrap_unavailable"):
        build_linux_bwrap_command(
            [str(executable)],
            runtime_roots=[str(runtime)],
            scratch_dir=str(scratch),
        )
