from __future__ import annotations

import time

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
