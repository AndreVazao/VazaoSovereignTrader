from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from PC_ENGINE.core.connector_runtime_manifest import build_runtime_manifest
from PC_ENGINE.core.connector_worker_sandbox import build_linux_bwrap_command


def test_packaged_cpython_imports_worker_and_serves_bounded_ipc():
    if os.environ.get("VST_CONNECTOR_RUNTIME_INTEGRATION") != "1":
        pytest.skip("real packaged CPython execution is reserved for the dedicated Linux CI job")
    if not sys_platform_linux():
        pytest.fail("dedicated runtime job must execute on Linux")

    runtime_root = Path(os.environ["VST_CONNECTOR_RUNTIME_ROOT"])
    executable = Path(os.environ["VST_CONNECTOR_RUNTIME_EXECUTABLE"])
    bwrap = shutil.which("bwrap")
    if not bwrap:
        pytest.fail("dedicated runtime job must install Bubblewrap")
    if not runtime_root.is_dir() or not executable.is_file():
        pytest.fail("packaged CPython runtime artifacts are missing")

    manifest = build_runtime_manifest(
        executable,
        required_directories=[runtime_root],
    )
    script = r'''
import importlib
import json
import os
import socket
import sys

sys.path.insert(0, os.path.join(os.environ["PYTHONHOME"], "app"))
worker = importlib.import_module("PC_ENGINE.core.isolated_connector_worker")
assert hasattr(worker, "IsolatedConnectorAdapter")

for name in (
    "json", "ssl", "sqlite3", "ctypes", "multiprocessing",
    "selectors", "hashlib", "zlib", "bz2", "lzma", "socket",
):
    importlib.import_module(name)

assert sys.prefix == os.environ["PYTHONHOME"], (sys.prefix, os.environ["PYTHONHOME"])
assert sys.base_prefix == os.environ["PYTHONHOME"]
assert all("site-packages" not in item for item in sys.path)
assert not os.path.exists("/etc/passwd")
assert not os.path.exists("/usr/bin/id")
assert "VST_HOST_ONLY_MARKER" not in os.environ
assert "PYTHONPATH" not in os.environ

client, server = socket.socketpair()
try:
    request = json.dumps({"op": "health", "nonce": "runtime-probe"}).encode()
    assert len(request) <= 256
    client.sendall(request)
    received = server.recv(256)
    assert received == request
finally:
    client.close()
    server.close()

network = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
network.settimeout(0.5)
try:
    try:
        network.connect(("127.0.0.1", 9))
    except OSError:
        pass
    else:
        raise AssertionError("sandbox network namespace unexpectedly permits loopback")
finally:
    network.close()

print(json.dumps({
    "python": sys.version.split()[0],
    "prefix": sys.prefix,
    "worker_import": "ok",
    "stdlib_imports": "ok",
    "bounded_ipc": "ok",
    "host_files_hidden": True,
    "network_denied": True,
}))
'''
    argv = build_linux_bwrap_command(
        [str(executable), "-S", "-c", script],
        runtime_manifest=manifest,
        python_home=str(runtime_root),
        runtime_library_path=str(runtime_root / "lib"),
        bwrap_path=bwrap,
        tmp_size_bytes=16 * 1024 * 1024,
        work_size_bytes=32 * 1024 * 1024,
    )
    result = subprocess.run(
        argv,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
        env={
            **os.environ,
            "PYTHONPATH": "/host-only/must-not-be-inherited",
            "VST_HOST_ONLY_MARKER": "must-not-enter-sandbox",
        },
    )
    assert result.returncode == 0, (
        f"packaged CPython failed in Bubblewrap ({result.returncode}): "
        f"{result.stderr[-3000:]}"
    )
    evidence = json.loads(result.stdout.strip().splitlines()[-1])
    assert evidence["worker_import"] == "ok"
    assert evidence["stdlib_imports"] == "ok"
    assert evidence["bounded_ipc"] == "ok"
    assert evidence["host_files_hidden"] is True
    assert evidence["network_denied"] is True


def sys_platform_linux() -> bool:
    import sys
    return sys.platform.startswith("linux")
