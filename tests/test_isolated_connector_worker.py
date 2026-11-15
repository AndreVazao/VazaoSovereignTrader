from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from PC_ENGINE.core.isolated_connector_worker import (
    IsolatedConnectorAdapter,
    IsolatedConnectorError,
)


class _EchoAdapter:
    def read(self, capability, request, *, timeout_seconds):
        return {"capability": capability, "value": request.get("value")}


class _SlowAdapter:
    def read(self, capability, request, *, timeout_seconds):
        time.sleep(2)
        return {"late": True}


def _echo_factory():
    return _EchoAdapter()


def _slow_factory():
    return _SlowAdapter()


def _broken_factory():
    raise RuntimeError("must_not_leak")


class _ChildProcessAdapter:
    def read(self, capability, request, *, timeout_seconds):
        marker_path = request["marker_path"]
        pid_path = request["pid_path"]
        child_script = (
            "import pathlib,sys,time; "
            "time.sleep(2.0); "
            "pathlib.Path(sys.argv[1]).write_text('child-survived', encoding='utf-8')"
        )
        child = subprocess.Popen([sys.executable, "-c", child_script, marker_path])
        Path(pid_path).write_text(str(child.pid), encoding="ascii")
        time.sleep(5.0)
        return {"child_pid": child.pid}


def _child_process_factory():
    return _ChildProcessAdapter()


def test_isolated_worker_returns_strict_json_snapshot():
    adapter = IsolatedConnectorAdapter(_echo_factory)
    result = adapter.read(
        "public_market_data.read",
        {"value": "snapshot"},
        timeout_seconds=2,
    )
    assert result == {
        "capability": "public_market_data.read",
        "value": "snapshot",
    }


def test_isolated_worker_terminates_adapter_after_timeout():
    adapter = IsolatedConnectorAdapter(
        _slow_factory,
        startup_grace_seconds=2.0,
    )
    started = time.monotonic()
    with pytest.raises(IsolatedConnectorError, match="connector_timeout"):
        adapter.read(
            "public_market_data.read",
            {},
            timeout_seconds=0.1,
        )
    assert time.monotonic() - started < 4.0


def test_isolated_worker_sanitizes_startup_failure():
    adapter = IsolatedConnectorAdapter(_broken_factory)
    with pytest.raises(IsolatedConnectorError, match="connector_startup_failed") as error:
        adapter.read(
            "public_market_data.read",
            {},
            timeout_seconds=1,
        )
    assert "must_not_leak" not in str(error.value)


def test_isolated_worker_rejects_oversized_request_before_spawn():
    adapter = IsolatedConnectorAdapter(_echo_factory, max_request_bytes=8)
    with pytest.raises(IsolatedConnectorError, match="request_too_large"):
        adapter.read(
            "public_market_data.read",
            {"value": "too long"},
            timeout_seconds=1,
        )


def test_isolated_worker_rejects_invalid_timeout():
    adapter = IsolatedConnectorAdapter(_echo_factory)
    with pytest.raises(IsolatedConnectorError, match="invalid_timeout"):
        adapter.read("public_market_data.read", {}, timeout_seconds=0)



class _EnvironmentAdapter:
    def read(self, capability, request, *, timeout_seconds):
        return {
            "credential_present": bool(os.environ.get("VST_TEST_API_TOKEN")),
            "ordinary_value": os.environ.get("VST_TEST_ORDINARY_VALUE"),
        }


def _environment_factory():
    return _EnvironmentAdapter()


def test_worker_removes_credential_shaped_environment_before_adapter(monkeypatch):
    monkeypatch.setenv("VST_TEST_API_TOKEN", "must_not_reach_adapter")
    monkeypatch.setenv("VST_TEST_ORDINARY_VALUE", "kept")
    adapter = IsolatedConnectorAdapter(_environment_factory)
    result = adapter.read(
        "public_market_data.read",
        {},
        timeout_seconds=2,
    )
    assert result == {
        "credential_present": False,
        "ordinary_value": "kept",
    }


def test_worker_rejects_out_of_range_os_resource_limits():
    with pytest.raises(ValueError, match="invalid_worker_memory_limit"):
        IsolatedConnectorAdapter(_echo_factory, memory_limit_mb=63)
    with pytest.raises(ValueError, match="invalid_worker_cpu_limit"):
        IsolatedConnectorAdapter(_echo_factory, cpu_time_limit_seconds=0)


def test_worker_accepts_explicit_bounded_os_resource_limits():
    adapter = IsolatedConnectorAdapter(
        _echo_factory,
        memory_limit_mb=512,
        cpu_time_limit_seconds=20,
    )
    result = adapter.read(
        "public_market_data.read",
        {"value": "bounded"},
        timeout_seconds=2,
    )
    assert result["value"] == "bounded"


def test_worker_timeout_terminates_spawned_descendants(tmp_path):
    marker_path = tmp_path / "child-survived.txt"
    pid_path = tmp_path / "child.pid"
    adapter = IsolatedConnectorAdapter(
        _child_process_factory,
        startup_grace_seconds=3.0,
    )

    with pytest.raises(IsolatedConnectorError, match="connector_timeout"):
        adapter.read(
            "public_market_data.read",
            {"marker_path": str(marker_path), "pid_path": str(pid_path)},
            timeout_seconds=1.5,
        )

    assert pid_path.exists(), "adapter did not start its child process"
    deadline = time.monotonic() + 2.5
    while time.monotonic() < deadline and not marker_path.exists():
        time.sleep(0.05)
    assert not marker_path.exists(), "adapter child outlived its worker"
