from __future__ import annotations

"""Deterministic adapter used only by the packaged-runtime CI enforcement probe."""

import os
import time
from collections.abc import Mapping


class RuntimeProbeAdapter:
    def read(
        self,
        capability: str,
        request: Mapping[str, object],
        *,
        timeout_seconds: float,
    ) -> Mapping[str, object]:
        if capability == "sleep":
            time.sleep(float(request.get("seconds", 5)))
        return {
            "capability": capability,
            "request": dict(request),
            "worker_pid": os.getpid(),
            "timeout_seconds": timeout_seconds,
        }


def adapter_factory() -> RuntimeProbeAdapter:
    return RuntimeProbeAdapter()
