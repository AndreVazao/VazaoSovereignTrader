"""Runtime shutdown supervision regression tests.

These tests use synthetic workers only. They verify that the engine does not
report OFF or close durable learning storage while a producer is still alive.
"""
from __future__ import annotations

import threading
from types import SimpleNamespace

from PC_ENGINE.core.engine import SovereignEngine


class MemoryProbe:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


def _engine(*, timeout: float = 0.05, status: str = "RUNNING") -> SovereignEngine:
    engine = object.__new__(SovereignEngine)
    engine.config = {"engine": {"shutdown_timeout_seconds": timeout}}
    engine.stop_event = threading.Event()
    engine.research_stop_event = threading.Event()
    engine.thread = None
    engine.research_thread = None
    engine.paper_collector = None
    engine.shared_intelligence_worker = None
    engine.state = SimpleNamespace(
        status=status,
        paper_collector={"running": False},
        operational={"learning_memory": {"state": "READY"}},
    )
    engine.lock = threading.RLock()
    engine.learning_memory = MemoryProbe()
    engine._closed = False
    engine._publish_observer_snapshot = lambda: None
    engine._persist_recovery = lambda: None
    engine.log = lambda *_args, **_kwargs: None
    return engine


def test_stop_joins_engine_worker_and_reports_off_only_after_exit() -> None:
    engine = _engine(timeout=0.5)
    engine.thread = threading.Thread(
        target=lambda: engine.stop_event.wait(30),
        name="vst-engine-loop",
        daemon=True,
    )
    engine.thread.start()

    engine.stop()

    assert not engine.thread.is_alive()
    assert engine.state.status == "OFF"
    assert engine.state.operational["shutdown"]["state"] == "STOPPED"
    assert engine.state.operational["shutdown"]["active_workers"] == []


def test_stop_reports_stopping_when_worker_ignores_stop_request() -> None:
    engine = _engine(timeout=0.05)
    release = threading.Event()
    engine.thread = threading.Thread(
        target=lambda: release.wait(5),
        name="synthetic-unresponsive-worker",
        daemon=True,
    )
    engine.thread.start()

    engine.stop()

    assert engine.thread.is_alive()
    assert engine.state.status == "STOPPING"
    assert engine.state.operational["shutdown"]["state"] == "STOPPING"
    assert engine.state.operational["shutdown"]["active_workers"] == [
        "engine"
    ]

    release.set()
    engine.thread.join(timeout=1)
    engine.stop()
    assert engine.state.status == "OFF"
    assert engine.state.operational["shutdown"]["state"] == "STOPPED"


def test_close_keeps_learning_memory_open_until_all_workers_exit() -> None:
    engine = _engine(timeout=0.05)
    release = threading.Event()
    engine.thread = threading.Thread(
        target=lambda: release.wait(5),
        name="synthetic-memory-producer",
        daemon=True,
    )
    engine.thread.start()

    assert engine.close() is False
    assert engine.learning_memory is not None
    assert engine.learning_memory.closed is False
    assert engine.state.operational["learning_memory_shutdown"]["state"] == (
        "DEFERRED_ACTIVE_WORKERS"
    )

    release.set()
    engine.thread.join(timeout=1)
    assert engine.close() is True
    assert engine.learning_memory is None
    assert engine.state.status == "OFF"
    assert engine.state.operational["shutdown"]["state"] == "STOPPED"
    assert engine.state.operational["learning_memory"]["state"] == "CLOSED"


def test_stop_never_clears_safe_mode_latch() -> None:
    engine = _engine(timeout=0.05, status="SAFE_MODE")

    engine.stop()

    assert engine.state.status == "SAFE_MODE"
    assert engine.state.operational["shutdown"]["state"] == "STOPPED"



def test_engine_cycle_wait_is_interruptible_on_stop() -> None:
    engine = _engine(timeout=0.5)
    cycle_started = threading.Event()
    engine.config["engine"]["cycle_seconds"] = 30
    engine.cycle = lambda: cycle_started.set()
    worker = threading.Thread(target=engine._loop, name="vst-engine-loop-test", daemon=True)

    worker.start()
    assert cycle_started.wait(1)
    engine.stop_event.set()
    worker.join(timeout=1)

    assert not worker.is_alive()
