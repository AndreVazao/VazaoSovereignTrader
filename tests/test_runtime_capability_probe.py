import pytest

from PC_ENGINE.core.runtime_capability_probe import (
    RuntimeProbeBlocked,
    run_read_only_probe,
)


class Adapter:
    name = "TEST"


def test_read_only_probe_verifies_non_empty_market_data():
    result = run_read_only_probe(
        Adapter(),
        capability="market_data_realtime",
        probe=lambda: {"last": 100.0},
        environment="PAPER",
    )
    assert result.verified
    assert result.evidence.startswith("runtime_probe:success:")


def test_probe_failure_is_not_verified():
    result = run_read_only_probe(
        Adapter(),
        capability="account_balances",
        probe=lambda: (_ for _ in ()).throw(RuntimeError("offline")),
        environment="REAL",
    )
    assert not result.verified
    assert "RuntimeError" in result.evidence


def test_empty_response_is_not_verified():
    result = run_read_only_probe(
        Adapter(),
        capability="market_data_historical",
        probe=lambda: [],
        environment="PAPER",
    )
    assert result.verified


def test_real_write_capability_is_blocked_from_read_only_probe():
    with pytest.raises(RuntimeProbeBlocked):
        run_read_only_probe(
            Adapter(),
            capability="real_order_submit",
            probe=lambda: {"id": "never-send"},
            environment="REAL",
        )
