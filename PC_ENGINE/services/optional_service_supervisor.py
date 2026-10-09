from __future__ import annotations

"""Fail-open lifecycle manager for explicitly allow-listed optional local services.

This module is intentionally not imported by the trading hot path. Callers should
acquire a lease only from low-priority work (for example, research/context tasks).
The supervisor never kills a process by image name and never stops a service it
found healthy before it started managing it.
"""

import os
import shutil
import subprocess
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from dataclasses import dataclass, field
from typing import Callable, Mapping, Sequence


class OptionalServiceUnavailable(RuntimeError):
    """Raised when an optional capability cannot be made available in time."""


@dataclass(frozen=True)
class ServiceSpec:
    name: str
    command: tuple[str, ...]
    healthcheck: Callable[[], bool]
    startup_timeout_seconds: float = 8.0
    poll_interval_seconds: float = 0.2
    shutdown_timeout_seconds: float = 2.0
    idle_grace_seconds: float = 20.0
    environment: Mapping[str, str] | None = None

    def __post_init__(self) -> None:
        if self.name not in {"ollama"}:
            raise ValueError("optional_service_not_allowlisted")
        if not self.command or not all(str(part).strip() for part in self.command):
            raise ValueError("optional_service_command_required")
        if self.startup_timeout_seconds <= 0 or self.poll_interval_seconds <= 0:
            raise ValueError("optional_service_timeouts_must_be_positive")
        if self.shutdown_timeout_seconds < 0 or self.idle_grace_seconds < 0:
            raise ValueError("optional_service_grace_must_not_be_negative")


def discover_ollama_spec(
    *,
    startup_timeout_seconds: float = 8.0,
    idle_grace_seconds: float = 20.0,
) -> ServiceSpec | None:
    """Build the allow-listed Ollama spec from an installed executable, without starting it."""
    executable = shutil.which("ollama")
    if not executable:
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        candidate = Path(local_app_data) / "Programs" / "Ollama" / "ollama.exe" if local_app_data else None
        if candidate is not None and candidate.is_file():
            executable = str(candidate)
    if not executable:
        return None
    return ServiceSpec(
        name="ollama",
        command=(executable, "serve"),
        healthcheck=ollama_healthcheck,
        startup_timeout_seconds=startup_timeout_seconds,
        idle_grace_seconds=idle_grace_seconds,
    )


def ollama_healthcheck(*, timeout_seconds: float = 0.5) -> bool:
    """Read-only local health probe; does not trigger model loading or inference."""
    request = urllib.request.Request(
        "http://127.0.0.1:11434/api/tags",
        headers={"Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=max(0.1, min(timeout_seconds, 2.0))) as response:
            return 200 <= response.status < 300
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


@dataclass
class _ServiceState:
    process: subprocess.Popen | None = None
    started_by_supervisor: bool = False
    leases: set[str] = field(default_factory=set)
    idle_timer: threading.Timer | None = None
    lock: threading.RLock = field(default_factory=threading.RLock)


class ServiceLease:
    """Idempotently releasable lease. Context-manager use is preferred."""

    def __init__(self, supervisor: "OptionalServiceSupervisor", name: str, lease_id: str):
        self._supervisor = supervisor
        self.name = name
        self._lease_id = lease_id
        self._released = False
        self._lock = threading.Lock()

    def release(self) -> None:
        with self._lock:
            if self._released:
                return
            self._released = True
        self._supervisor._release(self.name, self._lease_id)

    def __enter__(self) -> "ServiceLease":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.release()


class OptionalServiceSupervisor:
    """Lease-based supervisor for opt-in, low-priority local capabilities.

    A healthy service that pre-exists acquisition is borrowed, never stopped.
    Only the exact Popen instance launched here can be terminated by this class.
    Concurrent leases share one instance and defer idle shutdown until the last
    lease has been released for the configured grace period.
    """

    def __init__(
        self,
        specs: Sequence[ServiceSpec],
        *,
        popen: Callable[..., subprocess.Popen] = subprocess.Popen,
        monotonic: Callable[[], float] = time.monotonic,
        timer_factory: Callable[..., threading.Timer] = threading.Timer,
    ) -> None:
        self._specs = {spec.name: spec for spec in specs}
        if len(self._specs) != len(specs):
            raise ValueError("duplicate_optional_service_spec")
        if set(self._specs) - {"ollama"}:
            raise ValueError("optional_service_not_allowlisted")
        self._popen = popen
        self._monotonic = monotonic
        self._timer_factory = timer_factory
        self._states = {name: _ServiceState() for name in self._specs}

    def acquire(self, name: str) -> ServiceLease:
        spec = self._specs.get(name)
        state = self._states.get(name)
        if spec is None or state is None:
            raise OptionalServiceUnavailable("optional_service_not_configured")

        with state.lock:
            if state.idle_timer is not None:
                state.idle_timer.cancel()
                state.idle_timer = None

            process = state.process
            if process is not None and process.poll() is not None:
                state.process = None
                state.started_by_supervisor = False
                process = None

            if process is None:
                # A healthy endpoint may be owned by the user or another manager.
                # Borrow it without recording a process that we may later stop.
                if not self._safe_healthcheck(spec):
                    try:
                        process = self._popen(
                            list(spec.command),
                            stdin=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            shell=False,
                            close_fds=True,
                            env=dict(spec.environment) if spec.environment is not None else None,
                        )
                    except Exception as exc:
                        raise OptionalServiceUnavailable("optional_service_start_failed") from exc
                    state.process = process
                    state.started_by_supervisor = True
                    if not self._wait_healthy(spec, process):
                        self._stop_exact_process(spec, state, process)
                        raise OptionalServiceUnavailable("optional_service_startup_timeout")
                else:
                    state.process = None
                    state.started_by_supervisor = False
            elif not self._safe_healthcheck(spec):
                # A process we own but which has lost health must not leak forever.
                if state.started_by_supervisor and state.process is not None:
                    self._stop_exact_process(spec, state, state.process)
                raise OptionalServiceUnavailable("optional_service_unhealthy")

            import uuid
            lease_id = uuid.uuid4().hex
            state.leases.add(lease_id)
            return ServiceLease(self, name, lease_id)

    def snapshot(self) -> dict[str, dict[str, object]]:
        result: dict[str, dict[str, object]] = {}
        for name, state in self._states.items():
            with state.lock:
                process = state.process
                result[name] = {
                    "configured": True,
                    "started_by_supervisor": state.started_by_supervisor,
                    "owned_process_running": process is not None and process.poll() is None,
                    "active_leases": len(state.leases),
                    "idle_shutdown_pending": state.idle_timer is not None,
                }
        return result

    @staticmethod
    def _safe_healthcheck(spec: ServiceSpec) -> bool:
        try:
            return bool(spec.healthcheck())
        except Exception:
            return False

    def _wait_healthy(self, spec: ServiceSpec, process: subprocess.Popen) -> bool:
        deadline = self._monotonic() + spec.startup_timeout_seconds
        while self._monotonic() < deadline:
            if process.poll() is not None:
                return False
            if self._safe_healthcheck(spec):
                return True
            time.sleep(min(spec.poll_interval_seconds, max(0.0, deadline - self._monotonic())))
        return self._safe_healthcheck(spec) and process.poll() is None

    def _release(self, name: str, lease_id: str) -> None:
        state = self._states.get(name)
        spec = self._specs.get(name)
        if state is None or spec is None:
            return
        with state.lock:
            state.leases.discard(lease_id)
            if state.leases or not state.started_by_supervisor or state.process is None:
                return
            if state.idle_timer is not None:
                state.idle_timer.cancel()
            timer = self._timer_factory(
                spec.idle_grace_seconds,
                self._stop_if_idle,
                args=(name, state.process),
            )
            timer.daemon = True
            state.idle_timer = timer
            timer.start()

    def _stop_if_idle(self, name: str, expected_process: subprocess.Popen) -> None:
        state = self._states.get(name)
        spec = self._specs.get(name)
        if state is None or spec is None:
            return
        with state.lock:
            if state.leases or not state.started_by_supervisor or state.process is not expected_process:
                return
            self._stop_exact_process(spec, state, expected_process)
            state.idle_timer = None

    def _stop_exact_process(
        self, spec: ServiceSpec, state: _ServiceState, process: subprocess.Popen
    ) -> None:
        # Identity check prevents a stale timer from stopping a newer process.
        if state.process is not process or not state.started_by_supervisor:
            return
        try:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=spec.shutdown_timeout_seconds)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=max(0.1, spec.shutdown_timeout_seconds))
        except Exception:
            # A cleanup error must not escape into the trading loop.
            pass
        finally:
            state.process = None
            state.started_by_supervisor = False
