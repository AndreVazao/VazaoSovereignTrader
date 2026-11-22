from __future__ import annotations

import json
import time
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(os.environ["PYTHONHOME"]) / "app"))
from collections.abc import Mapping
from typing import Any

from PC_ENGINE.core.isolated_connector_worker import IsolatedConnectorAdapter


class ProbeAdapter:
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
            "worker_pid": __import__("os").getpid(),
        }


def adapter_factory() -> ProbeAdapter:
    return ProbeAdapter()


def main() -> None:
    adapter = IsolatedConnectorAdapter(
        adapter_factory,
        startup_grace_seconds=5,
        memory_limit_mb=256,
        cpu_time_limit_seconds=10,
    )
    result = adapter.read(
        "runtime-probe",
        {"nonce": "spawn-handshake", "bounded": True},
        timeout_seconds=3,
    )
    assert result["capability"] == "runtime-probe"
    assert result["request"]["nonce"] == "spawn-handshake"
    assert result["worker_pid"] != __import__("os").getpid()

    timeout_observed = False
    try:
        adapter.read("sleep", {"seconds": 5}, timeout_seconds=0.5)
    except Exception as exc:
        timeout_observed = str(exc) == "connector_timeout"
    assert timeout_observed, "worker timeout was not enforced"

    import multiprocessing
    assert multiprocessing.active_children() == [], "worker process survived cleanup"
    print(json.dumps({
        "multiprocessing_spawn": "ok",
        "startup_handshake": "ok",
        "bounded_request_response": "ok",
        "timeout": "ok",
        "process_cleanup": "ok",
    }, sort_keys=True))


if __name__ == "__main__":
    main()
