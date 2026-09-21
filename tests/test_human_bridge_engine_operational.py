from __future__ import annotations

import time

from PC_ENGINE.core.engine import RuntimeState, SovereignEngine
from PC_ENGINE.human_bridge.bridge import HumanInteractionBridge
from PC_ENGINE.human_bridge.watchdog import HumanBridgeWatchdog


def _engine(tmp_path):
    engine = SovereignEngine.__new__(SovereignEngine)
    engine.config = {
        "human_bridge": {
            "enabled": True,
            "data_dir": str(tmp_path),
            "mobile_timeout_seconds": 10,
            "pc_timeout_seconds": 10,
            "responded_timeout_seconds": 30,
        }
    }
    engine.state = RuntimeState(mode="PAPER")
    engine.human_bridge = HumanInteractionBridge(str(tmp_path))
    engine.human_bridge_watchdog = HumanBridgeWatchdog(
        engine.human_bridge,
        engine.config["human_bridge"],
    )
    engine._human_bridge_operational_last_state = None
    engine.log = lambda *_args, **_kwargs: None
    return engine


def test_human_bridge_state_is_telemetry_only_when_stale(tmp_path):
    engine = _engine(tmp_path)
    engine.human_bridge_watchdog.heartbeat("mobile")
    engine.human_bridge_watchdog.heartbeat("pc")

    healthy = engine.refresh_human_bridge_operational_state(time.time())
    assert healthy["state"] == "HEALTHY"
    assert healthy["trading_impact"] == "NONE"
    assert healthy["action"] == "CONTINUE_TRADING"

    stale = engine.refresh_human_bridge_operational_state(time.time() + 11)
    assert stale["state"] == "BRIDGE_UNAVAILABLE"
    assert stale["trading_impact"] == "NONE"
    assert stale["action"] == "CONTINUE_TRADING"
    assert engine.state.status == "OFF"


def test_stale_bridge_blocks_only_pending_human_interaction(tmp_path):
    engine = _engine(tmp_path)
    engine.human_bridge_watchdog.heartbeat("mobile")
    engine.human_bridge_watchdog.heartbeat("pc")
    engine.human_bridge.create_request(
        "browser",
        "OTP",
        "Intervenção",
        "Aguardar operador",
    )

    report = engine.refresh_human_bridge_operational_state(time.time() + 11)

    assert report["state"] == "BRIDGE_UNAVAILABLE"
    assert report["human_interaction_required"] == 1
    assert report["action"] == "HUMAN_INTERACTION_BLOCKED"
    assert report["trading_impact"] == "NONE"
    assert engine.state.status == "OFF"
