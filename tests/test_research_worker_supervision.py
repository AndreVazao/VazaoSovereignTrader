from __future__ import annotations

import threading
import time
from types import SimpleNamespace

from PC_ENGINE.core.engine import SovereignEngine
from PC_ENGINE.research.worker import ResearchWorker


def test_research_worker_publishes_heartbeat_and_success(tmp_path):
    worker = ResearchWorker(str(tmp_path))
    worker.process_pending = lambda max_items=1: {"processed": 0}
    stop = threading.Event()
    thread = threading.Thread(target=worker.run_forever, args=(stop, 0.25), daemon=True)

    thread.start()
    deadline = time.monotonic() + 2
    snapshot = worker.supervision_snapshot()
    while snapshot["iterations"] == 0 and time.monotonic() < deadline:
        time.sleep(0.01)
        snapshot = worker.supervision_snapshot()
    stop.set()
    thread.join(timeout=1)

    assert not thread.is_alive()
    assert snapshot["iterations"] >= 1
    assert snapshot["heartbeat_ts"] > 0
    assert snapshot["last_success_ts"] > 0
    assert snapshot["last_error_type"] == ""


def _engine_for_supervision(worker_thread, worker, *, stop_requested=False):
    engine = object.__new__(SovereignEngine)
    engine.config = {"research": {"enabled": True, "worker_interval_seconds": 1}}
    engine.research_thread = worker_thread
    engine.research_worker = worker
    engine.research_stop_event = threading.Event()
    if stop_requested:
        engine.research_stop_event.set()
    engine.state = SimpleNamespace(operational={})
    return engine


def test_dead_research_worker_is_reported_as_failed_not_silently_restarted():
    worker = SimpleNamespace(supervision_snapshot=lambda: {})
    engine = _engine_for_supervision(None, worker)

    report = engine._supervise_research_worker()

    assert report["state"] == "NOT_STARTED"
    assert report["critical"] is False


def test_unexpected_research_thread_exit_is_visible_and_non_critical():
    worker = SimpleNamespace(supervision_snapshot=lambda: {})
    dead_thread = threading.Thread(target=lambda: None)
    dead_thread.start()
    dead_thread.join(timeout=1)
    engine = _engine_for_supervision(dead_thread, worker)

    report = engine._supervise_research_worker()

    assert report["state"] == "FAILED"
    assert report["thread_alive"] is False
    assert report["critical"] is False


def test_research_worker_stop_is_not_misclassified_as_failure():
    worker = SimpleNamespace(supervision_snapshot=lambda: {})
    dead_thread = threading.Thread(target=lambda: None)
    dead_thread.start()
    dead_thread.join(timeout=1)
    engine = _engine_for_supervision(dead_thread, worker, stop_requested=True)

    report = engine._supervise_research_worker()

    assert report["state"] == "STOPPED"
    assert report["critical"] is False


def test_live_research_thread_with_old_heartbeat_is_reported_stale():
    release = threading.Event()
    live_thread = threading.Thread(target=lambda: release.wait(5), daemon=True)
    live_thread.start()
    worker = SimpleNamespace(
        supervision_snapshot=lambda: {
            "heartbeat_ts": time.time() - 30,
            "last_success_ts": time.time() - 35,
            "iterations": 4,
            "last_error_type": "",
        }
    )
    engine = _engine_for_supervision(live_thread, worker)

    try:
        report = engine._supervise_research_worker()
        assert report["state"] == "STALE"
        assert report["thread_alive"] is True
        assert report["critical"] is False
    finally:
        release.set()
        live_thread.join(timeout=1)
