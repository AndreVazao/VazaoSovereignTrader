from __future__ import annotations

import ctypes
import os
from typing import Any


MIN_MEMORY_LIMIT_MB = 64
MAX_MEMORY_LIMIT_MB = 2048
MIN_CPU_TIME_SECONDS = 1
MAX_CPU_TIME_SECONDS = 120


def validate_worker_limits(memory_limit_mb: int, cpu_time_limit_seconds: int) -> None:
    if (
        isinstance(memory_limit_mb, bool)
        or not isinstance(memory_limit_mb, int)
        or not MIN_MEMORY_LIMIT_MB <= memory_limit_mb <= MAX_MEMORY_LIMIT_MB
    ):
        raise ValueError("invalid_worker_memory_limit")
    if (
        isinstance(cpu_time_limit_seconds, bool)
        or not isinstance(cpu_time_limit_seconds, int)
        or not MIN_CPU_TIME_SECONDS
        <= cpu_time_limit_seconds
        <= MAX_CPU_TIME_SECONDS
    ):
        raise ValueError("invalid_worker_cpu_limit")


def _bounded_limits(
    requested_soft: int,
    requested_hard: int,
    existing_soft: int,
    existing_hard: int,
    infinity: int,
) -> tuple[int, int]:
    """Lower inherited limits without ever raising an existing soft or hard cap."""
    soft = (
        requested_soft
        if existing_soft == infinity
        else min(requested_soft, existing_soft)
    )
    hard = (
        requested_hard
        if existing_hard == infinity
        else min(requested_hard, existing_hard)
    )
    return min(soft, hard), hard


def apply_child_resource_limits(
    memory_limit_mb: int,
    cpu_time_limit_seconds: int,
) -> None:
    """Apply POSIX hard address-space and CPU-time limits inside the worker."""
    validate_worker_limits(memory_limit_mb, cpu_time_limit_seconds)
    if os.name == "nt":
        # Windows limits are applied by the parent Job Object before the
        # worker is released to execute adapter code.
        return

    try:
        import resource
    except ImportError:
        raise RuntimeError("worker_resource_limits_unavailable") from None

    if not hasattr(resource, "RLIMIT_AS") or not hasattr(resource, "RLIMIT_CPU"):
        raise RuntimeError("worker_resource_limits_unavailable")

    memory_bytes = memory_limit_mb * 1024 * 1024
    memory_soft, memory_hard = resource.getrlimit(resource.RLIMIT_AS)
    bounded_memory_soft, bounded_memory_hard = _bounded_limits(
        memory_bytes,
        memory_bytes,
        memory_soft,
        memory_hard,
        resource.RLIM_INFINITY,
    )
    if bounded_memory_soft <= 0 or bounded_memory_hard < bounded_memory_soft:
        raise RuntimeError("worker_resource_limits_unavailable")
    resource.setrlimit(
        resource.RLIMIT_AS, (bounded_memory_soft, bounded_memory_hard)
    )

    cpu_soft, cpu_hard = resource.getrlimit(resource.RLIMIT_CPU)
    bounded_cpu_soft, bounded_cpu_hard = _bounded_limits(
        cpu_time_limit_seconds,
        cpu_time_limit_seconds + 1,
        cpu_soft,
        cpu_hard,
        resource.RLIM_INFINITY,
    )
    if bounded_cpu_soft <= 0 or bounded_cpu_hard < bounded_cpu_soft:
        raise RuntimeError("worker_resource_limits_unavailable")
    resource.setrlimit(
        resource.RLIMIT_CPU, (bounded_cpu_soft, bounded_cpu_hard)
    )


class _IoCounters(ctypes.Structure):
    _fields_ = [
        ("ReadOperationCount", ctypes.c_ulonglong),
        ("WriteOperationCount", ctypes.c_ulonglong),
        ("OtherOperationCount", ctypes.c_ulonglong),
        ("ReadTransferCount", ctypes.c_ulonglong),
        ("WriteTransferCount", ctypes.c_ulonglong),
        ("OtherTransferCount", ctypes.c_ulonglong),
    ]


class _BasicLimitInformation(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_longlong),
        ("PerJobUserTimeLimit", ctypes.c_longlong),
        ("LimitFlags", ctypes.c_ulong),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", ctypes.c_ulong),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", ctypes.c_ulong),
        ("SchedulingClass", ctypes.c_ulong),
    ]


class _ExtendedLimitInformation(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", _BasicLimitInformation),
        ("IoInfo", _IoCounters),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


def assign_windows_job_limits(
    process: Any,
    memory_limit_mb: int,
    cpu_time_limit_seconds: int,
) -> Any:
    """Assign a spawned worker to a kill-on-close Job Object with hard limits.

    The returned handle must remain open for the worker's entire lifetime.
    """
    validate_worker_limits(memory_limit_mb, cpu_time_limit_seconds)
    if os.name != "nt":
        raise RuntimeError("windows_job_object_unavailable")

    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    kernel32.SetInformationJobObject.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
    ]
    kernel32.SetInformationJobObject.restype = wintypes.BOOL
    kernel32.AssignProcessToJobObject.argtypes = [
        wintypes.HANDLE,
        wintypes.HANDLE,
    ]
    kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL

    job = kernel32.CreateJobObjectW(None, None)
    if not job:
        raise RuntimeError("worker_job_object_create_failed")

    info = _ExtendedLimitInformation()
    info.BasicLimitInformation.LimitFlags = (
        0x0002  # JOB_OBJECT_LIMIT_PROCESS_TIME
        | 0x0100  # JOB_OBJECT_LIMIT_PROCESS_MEMORY
        | 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    )
    info.BasicLimitInformation.PerProcessUserTimeLimit = (
        cpu_time_limit_seconds * 10_000_000
    )
    info.ProcessMemoryLimit = memory_limit_mb * 1024 * 1024

    try:
        if not kernel32.SetInformationJobObject(
            job,
            9,  # JobObjectExtendedLimitInformation
            ctypes.byref(info),
            ctypes.sizeof(info),
        ):
            raise RuntimeError("worker_job_object_configure_failed")

        popen = getattr(process, "_popen", None)
        process_handle = getattr(popen, "_handle", None)
        if process_handle is None:
            raise RuntimeError("worker_process_handle_unavailable")
        try:
            process_handle_value = int(process_handle)
        except (TypeError, ValueError, OverflowError):
            process_handle_value = process_handle
        if not kernel32.AssignProcessToJobObject(
            job, wintypes.HANDLE(process_handle_value)
        ):
            raise RuntimeError("worker_job_object_assign_failed")
        return job
    except BaseException:
        kernel32.CloseHandle(job)
        raise


def close_windows_job(job: Any) -> None:
    if job is None or os.name != "nt":
        return
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    kernel32.CloseHandle(job)
