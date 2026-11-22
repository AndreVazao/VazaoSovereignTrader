from __future__ import annotations

import json

import pytest

from PC_ENGINE.core import connector_worker_bootstrap as bootstrap


class _Adapter:
    def read(self, capability, request, *, timeout_seconds):
        assert capability == "public_market_data.read"
        assert timeout_seconds == 2.0
        return {"echo": request["symbol"]}


def _payload():
    return {
        "factory": "tests.fake:Factory",
        "capability": "public_market_data.read",
        "request": {"symbol": "BTC/USDT"},
        "timeout_seconds": 2.0,
        "memory_limit_mb": 128,
        "cpu_time_limit_seconds": 5,
    }


def test_bootstrap_executes_factory_only_after_resource_limits(monkeypatch):
    events = []
    monkeypatch.setattr(
        bootstrap,
        "apply_child_resource_limits",
        lambda memory, cpu: events.append(("limits", memory, cpu)),
    )

    def resolve(reference):
        events.append(("factory", reference))
        return _Adapter

    result = bootstrap.execute_request(_payload(), factory_resolver=resolve)

    assert result == {"ok": True, "data": {"echo": "BTC/USDT"}}
    assert events == [
        ("limits", 128, 5),
        ("factory", "tests.fake:Factory"),
    ]


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("timeout_seconds", True, "invalid_timeout"),
        ("timeout_seconds", float("nan"), "invalid_timeout"),
        ("memory_limit_mb", True, "invalid_memory_limit"),
        ("cpu_time_limit_seconds", 0.5, "invalid_cpu_limit"),
        ("capability", "", "invalid_capability"),
        ("request", [], "invalid_request"),
    ],
)
def test_bootstrap_rejects_invalid_worker_request(field, value, error, monkeypatch):
    monkeypatch.setattr(bootstrap, "apply_child_resource_limits", lambda *_: None)
    payload = _payload()
    payload[field] = value
    with pytest.raises(ValueError, match=error):
        bootstrap.execute_request(payload, factory_resolver=lambda _: _Adapter)


def test_bootstrap_rejects_extra_payload_fields_before_factory(monkeypatch):
    monkeypatch.setattr(bootstrap, "apply_child_resource_limits", lambda *_: None)
    payload = _payload()
    payload["api_key"] = "must-never-be-accepted"
    called = []
    with pytest.raises(ValueError, match="invalid_worker_request"):
        bootstrap.execute_request(payload, factory_resolver=lambda _: called.append(True))
    assert called == []


def test_bootstrap_bounds_serialized_response(monkeypatch):
    monkeypatch.setattr(bootstrap, "apply_child_resource_limits", lambda *_: None)

    class LargeAdapter:
        def read(self, *_args, **_kwargs):
            return {"value": "x" * bootstrap.MAX_RESPONSE_BYTES}

    with pytest.raises(ValueError, match="response_too_large"):
        bootstrap.execute_request(_payload(), factory_resolver=lambda _: LargeAdapter)


def test_factory_reference_is_restricted_to_importable_names():
    for value in ("../module:Factory", "module;os:system", "module:Factory()"):
        with pytest.raises(ValueError, match="invalid_factory_reference"):
            bootstrap._resolve_factory(value)
