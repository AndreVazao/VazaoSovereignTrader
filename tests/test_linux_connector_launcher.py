from __future__ import annotations

import os
import shutil
import sys
import time
from pathlib import Path

import pytest

from PC_ENGINE.core.connector_runtime_manifest import (
    RuntimeManifest,
    RuntimeMount,
    build_runtime_manifest,
)
from PC_ENGINE.core.linux_connector_launcher import (
    LinuxBubblewrapConnectorAdapter,
    LinuxSandboxLaunchError,
)


def _adapter(manifest: RuntimeManifest) -> LinuxBubblewrapConnectorAdapter:
    return LinuxBubblewrapConnectorAdapter(
        "PC_ENGINE.core.connector_runtime_probe:adapter_factory",
        runtime_manifest=manifest,
        python_home="/opt/vst-runtime",
        bwrap_path="/usr/bin/bwrap",
    )


def test_launcher_rejects_non_linux_without_fallback(monkeypatch):
    manifest = RuntimeManifest(
        executable=Path("/opt/vst-runtime/bin/python"),
        mounts=(
            RuntimeMount(
                Path("/opt/vst-runtime/bin/python"),
                Path("/opt/vst-runtime/bin/python"),
                False,
            ),
        ),
    )
    adapter = _adapter(manifest)
    monkeypatch.setattr(sys, "platform", "win32")

    with pytest.raises(
        LinuxSandboxLaunchError,
        match="linux_sandbox_platform_required",
    ):
        adapter.read("public_market_data.read", {}, timeout_seconds=1)



def test_launcher_rejects_non_read_only_capability_before_launch():
    manifest = RuntimeManifest(
        executable=Path("/opt/vst-runtime/bin/python"),
        mounts=(
            RuntimeMount(
                Path("/opt/vst-runtime/bin/python"),
                Path("/opt/vst-runtime/bin/python"),
                False,
            ),
        ),
    )
    adapter = _adapter(manifest)

    with pytest.raises(
        LinuxSandboxLaunchError,
        match="capability_not_read_only",
    ):
        adapter.read("orders.create", {"symbol": "BTC/USDT"}, timeout_seconds=1)


def test_launcher_rejects_oversized_request_before_launch(monkeypatch):
    manifest = RuntimeManifest(
        executable=Path("/opt/vst-runtime/bin/python"),
        mounts=(
            RuntimeMount(
                Path("/opt/vst-runtime/bin/python"),
                Path("/opt/vst-runtime/bin/python"),
                False,
            ),
        ),
    )
    adapter = LinuxBubblewrapConnectorAdapter(
        "PC_ENGINE.core.connector_runtime_probe:adapter_factory",
        runtime_manifest=manifest,
        python_home="/opt/vst-runtime",
        max_request_bytes=32,
    )
    monkeypatch.setattr(
        "PC_ENGINE.core.linux_connector_launcher.build_linux_bwrap_command",
        lambda *args, **kwargs: pytest.fail("oversized request reached launcher"),
    )

    with pytest.raises(LinuxSandboxLaunchError, match="request_too_large"):
        adapter.read(
            "public_market_data.read",
            {"payload": "x" * 100},
            timeout_seconds=1,
        )


def test_launcher_fails_closed_when_bubblewrap_is_unavailable(monkeypatch):
    manifest = RuntimeManifest(
        executable=Path("/opt/vst-runtime/bin/python"),
        mounts=(
            RuntimeMount(
                Path("/opt/vst-runtime/bin/python"),
                Path("/opt/vst-runtime/bin/python"),
                False,
            ),
        ),
    )
    adapter = _adapter(manifest)

    def deny_launch(*args, **kwargs):
        from PC_ENGINE.core.connector_worker_sandbox import SandboxUnavailable
        raise SandboxUnavailable("bwrap_missing")

    monkeypatch.setattr(
        "PC_ENGINE.core.linux_connector_launcher.build_linux_bwrap_command",
        deny_launch,
    )
    monkeypatch.setattr(
        "PC_ENGINE.core.linux_connector_launcher.subprocess.Popen",
        lambda *args, **kwargs: pytest.fail("sandbox denial attempted fallback"),
    )

    with pytest.raises(
        LinuxSandboxLaunchError,
        match="sandbox_configuration_denied",
    ):
        adapter.read("public_market_data.read", {}, timeout_seconds=1)


def test_packaged_runtime_is_launched_by_trusted_parent_inside_bubblewrap():
    if os.environ.get("VST_CONNECTOR_RUNTIME_INTEGRATION") != "1":
        pytest.skip("real parent-launcher execution is reserved for dedicated Linux CI")
    if not sys.platform.startswith("linux"):
        pytest.fail("dedicated parent-launcher job must execute on Linux")

    runtime_root = Path(os.environ["VST_CONNECTOR_RUNTIME_ROOT"])
    executable = Path(os.environ["VST_CONNECTOR_RUNTIME_EXECUTABLE"])
    bwrap = shutil.which("bwrap")
    if not runtime_root.is_dir() or not executable.is_file() or not bwrap:
        pytest.fail("packaged runtime or Bubblewrap is missing")

    manifest = build_runtime_manifest(
        executable,
        required_directories=[runtime_root],
    )
    adapter = LinuxBubblewrapConnectorAdapter(
        "PC_ENGINE.core.connector_runtime_probe:adapter_factory",
        runtime_manifest=manifest,
        python_home=str(runtime_root),
        runtime_library_path=str(runtime_root / "lib"),
        bwrap_path=bwrap,
        memory_limit_mb=384,
        cpu_time_limit_seconds=10,
    )
    result = adapter.read(
        "public_market_data.read",
        {"nonce": "trusted-parent-launch", "bounded": True},
        timeout_seconds=4,
    )
    assert result["capability"] == "public_market_data.read"
    assert result["request"]["nonce"] == "trusted-parent-launch"
    assert isinstance(result["worker_pid"], int)

    started = time.monotonic()
    with pytest.raises(LinuxSandboxLaunchError, match="sandbox_worker_timeout"):
        adapter.read("public_market_data.read", {"sleep_seconds": 5}, timeout_seconds=0.5)
    assert time.monotonic() - started < 4.0



def test_launcher_rejects_root_service_identity_without_fallback(monkeypatch):
    manifest = RuntimeManifest(
        executable=Path("/opt/vst-runtime/bin/python"),
        mounts=(
            RuntimeMount(
                Path("/opt/vst-runtime/bin/python"),
                Path("/opt/vst-runtime/bin/python"),
                False,
            ),
        ),
    )
    adapter = _adapter(manifest)
    monkeypatch.setattr(
        "PC_ENGINE.core.linux_connector_launcher.os.geteuid",
        lambda: 0,
    )
    monkeypatch.setattr(
        "PC_ENGINE.core.linux_connector_launcher.build_linux_bwrap_command",
        lambda *args, **kwargs: ["/usr/bin/bwrap", "--version"],
    )
    monkeypatch.setattr(
        "PC_ENGINE.core.linux_connector_launcher.subprocess.Popen",
        lambda *args, **kwargs: pytest.fail("root-owned runtime policy must deny before launch"),
    )

    with pytest.raises(
        LinuxSandboxLaunchError,
        match="sandbox_configuration_denied",
    ):
        adapter.read("public_market_data.read", {}, timeout_seconds=1)
