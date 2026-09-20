from __future__ import annotations

import threading

from PC_ENGINE.core.engine import RuntimeState, SovereignEngine


def test_real_start_blocks_before_running_when_account_reconciliation_fails():
    engine = object.__new__(SovereignEngine)
    engine.thread = None
    engine.mode = "REAL"
    engine.execution_intents = {}
    engine.state = RuntimeState(mode="REAL")
    engine.state.status = "OFF"
    engine.stop_event = threading.Event()
    engine.research_stop_event = threading.Event()
    engine.config = {"engine": {"preflight_required": True}}
    engine.run_preflight = lambda: {"ok": True, "errors": [], "warnings": []}
    engine.reconcile_account_state = lambda: {"ok": False, "status": "BLOCKED", "reason": "mismatch"}
    engine.log = lambda *args, **kwargs: None

    engine.start()

    assert engine.state.status == "SAFE_MODE"
    assert not engine.stop_event.is_set()
