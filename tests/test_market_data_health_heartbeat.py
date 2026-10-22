from __future__ import annotations

import math

from PC_ENGINE.tools.run_market_data_collector import _health_heartbeat_interval_seconds


def test_health_heartbeat_interval_defaults_to_ten_seconds():
    assert _health_heartbeat_interval_seconds({}) == 10.0


def test_health_heartbeat_interval_is_bounded():
    assert _health_heartbeat_interval_seconds({"health_heartbeat_seconds": 0.1}) == 1.0
    assert _health_heartbeat_interval_seconds({"health_heartbeat_seconds": 120}) == 10.0
    assert _health_heartbeat_interval_seconds({"health_heartbeat_seconds": 15}) == 10.0
    assert _health_heartbeat_interval_seconds({
        "health_heartbeat_seconds": 8,
        "health_stale_seconds": 12,
    }) == 4.0


def test_health_heartbeat_interval_handles_invalid_values():
    assert _health_heartbeat_interval_seconds({"health_heartbeat_seconds": "bad"}) == 10.0
    assert _health_heartbeat_interval_seconds({"health_heartbeat_seconds": math.inf}) == 10.0
