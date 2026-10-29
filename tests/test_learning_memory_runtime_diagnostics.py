from __future__ import annotations

from types import SimpleNamespace

from PC_ENGINE.diagnostics.learning_memory_runtime import build_learning_memory_runtime_diagnostics


class FakeThread:
    def __init__(self, alive: bool):
        self.alive = alive

    def is_alive(self) -> bool:
        return self.alive


class FakeMemory:
    pass


class FakeAutonomousResearch:
    def __init__(self, memory, failures=0, error=""):
        self.learning_memory = memory
        self.failures = failures
        self.error = error

    def snapshot(self):
        return {"durable_memory": {"write_failures": self.failures, "last_error": self.error}}


def make_engine(
    *, alive=True, research_alive=True, failures=0, error="", enabled=True,
    wired=True, closed=False, observation_enabled=True, research_thread_present=True,
):
    memory = FakeMemory() if enabled else None
    autonomous = FakeAutonomousResearch(memory if wired else None, failures, error)
    return SimpleNamespace(
        _closed=closed,
        thread=FakeThread(alive),
        research_thread=FakeThread(research_alive) if research_thread_present else None,
        learning_memory=memory,
        autonomous_research=autonomous,
        config={"research": {"enabled": observation_enabled, "autonomous_observation_enabled": True}},
        state=SimpleNamespace(operational={"learning_memory": {"enabled": enabled, "state": "READY" if enabled else "DISABLED"}}),
    )


def test_runtime_diagnostics_reports_running_only_when_both_runtime_threads_and_memory_are_ready():
    result = build_learning_memory_runtime_diagnostics(make_engine())
    assert result["status"] == "RUNNING"
    assert result["engine_loop"] == "RUNNING"
    assert result["research_worker"] == "RUNNING"
    assert result["memory_consumer_wired"] is True
    assert result["learning_quality_verified"] is False
    assert result["execution_authorized"] is False


def test_runtime_diagnostics_does_not_claim_running_when_engine_loop_stopped():
    result = build_learning_memory_runtime_diagnostics(make_engine(alive=False))
    assert result["status"] == "STOPPED"
    assert result["reason"] == "engine_loop_not_running"


def test_runtime_diagnostics_degrades_when_research_worker_is_missing_or_stopped():
    stopped = build_learning_memory_runtime_diagnostics(make_engine(research_alive=False))
    assert stopped["status"] == "DEGRADED"
    assert stopped["reason"] == "research_worker_not_running"
    assert stopped["research_worker"] == "STOPPED"

    missing = build_learning_memory_runtime_diagnostics(make_engine(research_thread_present=False))
    assert missing["status"] == "UNKNOWN"
    assert missing["reason"] == "research_worker_state_unavailable"
    assert missing["research_worker"] == "UNKNOWN"


def test_runtime_diagnostics_degrades_on_missing_memory_or_disconnected_consumer():
    missing = build_learning_memory_runtime_diagnostics(make_engine(enabled=False))
    assert missing["status"] == "DEGRADED"
    assert missing["reason"] == "durable_memory_not_available"

    disconnected = build_learning_memory_runtime_diagnostics(make_engine(wired=False))
    assert disconnected["status"] == "DEGRADED"
    assert disconnected["memory_consumer_wired"] is False


def test_runtime_diagnostics_surfaces_write_failures_without_claiming_healthy():
    result = build_learning_memory_runtime_diagnostics(make_engine(failures=2, error="OSError"))
    assert result["status"] == "DEGRADED"
    assert result["write_failures"] == 2
    assert result["last_error"] == "OSError"


def test_runtime_diagnostics_reports_terminal_close_and_disabled_observation():
    closed = build_learning_memory_runtime_diagnostics(make_engine(closed=True))
    assert closed["status"] == "CLOSED"

    disabled = build_learning_memory_runtime_diagnostics(make_engine(observation_enabled=False))
    assert disabled["status"] == "DISABLED"
