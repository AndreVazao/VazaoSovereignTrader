from __future__ import annotations

import threading
import time

import pytest

from PC_ENGINE.services.optional_service_supervisor import (
    OptionalServiceSupervisor,
    OptionalServiceUnavailable,
    ServiceSpec,
)


class FakeProcess:
    def __init__(self, *_args, **_kwargs):
        self.returncode = None
        self.terminated = False
        self.killed = False
        self.waited = False

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminated = True
        self.returncode = 0

    def kill(self):
        self.killed = True
        self.returncode = -9

    def wait(self, timeout=None):
        self.waited = True
        return self.returncode


class ImmediateTimer:
    def __init__(self, _delay, function, args=()):
        self.function = function
        self.args = args
        self.daemon = False
        self.cancelled = False

    def start(self):
        if not self.cancelled:
            self.function(*self.args)

    def cancel(self):
        self.cancelled = True


def spec(health, *, idle=0):
    return ServiceSpec(
        name="ollama",
        command=("ollama", "serve"),
        healthcheck=health,
        startup_timeout_seconds=0.4,
        poll_interval_seconds=0.01,
        shutdown_timeout_seconds=0.1,
        idle_grace_seconds=idle,
    )


def test_reuses_healthy_external_service_without_start_or_stop():
    starts = []
    supervisor = OptionalServiceSupervisor([spec(lambda: True)], popen=lambda *a, **k: starts.append(a))
    with supervisor.acquire("ollama"):
        state = supervisor.snapshot()["ollama"]
        assert state["started_by_supervisor"] is False
        assert state["active_leases"] == 1
    assert starts == []
    assert supervisor.snapshot()["ollama"]["active_leases"] == 0


def test_starts_owned_process_and_stops_only_after_last_lease():
    healthy = threading.Event()
    processes = []

    def start(*args, **kwargs):
        proc = FakeProcess(*args, **kwargs)
        processes.append(proc)
        healthy.set()
        return proc

    supervisor = OptionalServiceSupervisor(
        [spec(healthy.is_set)], popen=start, timer_factory=ImmediateTimer
    )
    first = supervisor.acquire("ollama")
    second = supervisor.acquire("ollama")
    assert len(processes) == 1
    first.release()
    assert processes[0].terminated is False
    second.release()
    assert processes[0].terminated is True
    assert supervisor.snapshot()["ollama"]["owned_process_running"] is False


def test_startup_timeout_terminates_exact_process_and_fails_open_to_caller():
    process = FakeProcess()
    supervisor = OptionalServiceSupervisor(
        [spec(lambda: False)], popen=lambda *a, **k: process, timer_factory=ImmediateTimer
    )
    with pytest.raises(OptionalServiceUnavailable, match="startup_timeout"):
        supervisor.acquire("ollama")
    assert process.terminated is True


def test_unknown_services_are_not_started():
    starts = []
    supervisor = OptionalServiceSupervisor([spec(lambda: True)], popen=lambda *a, **k: starts.append(a))
    with pytest.raises(OptionalServiceUnavailable, match="not_configured"):
        supervisor.acquire("tailscale")
    assert starts == []


def test_service_name_allowlist_is_enforced():
    with pytest.raises(ValueError, match="not_allowlisted"):
        ServiceSpec(name="arbitrary", command=("cmd",), healthcheck=lambda: True)


def test_double_release_is_idempotent():
    supervisor = OptionalServiceSupervisor(
        [spec(lambda: True)], popen=lambda *a, **k: pytest.fail("must borrow external service")
    )
    lease = supervisor.acquire("ollama")
    lease.release()
    lease.release()
    assert supervisor.snapshot()["ollama"]["active_leases"] == 0
