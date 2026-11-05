from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PC_ENGINE.learning.sqlite_memory import SQLiteLearningMemory


def test_committed_learning_record_survives_ungraceful_process_exit(tmp_path):
    database = tmp_path / "vault" / "learning" / "sovereign-learning.sqlite3"
    repository_root = Path(__file__).resolve().parents[1]
    child_code = """
import os
import sys
from PC_ENGINE.learning.sqlite_memory import SQLiteLearningMemory

memory = SQLiteLearningMemory(sys.argv[1])
record = memory.put(
    key="crash-recovery.synthetic.paper",
    value={"samples": 19, "net_edge_bps": 2.4},
    department="analysis",
    provenance="synthetic-process-crash-test",
    status="testing",
    confidence=0.7,
)
assert record.version == 1
# Simulate abrupt process death: deliberately skip close(), context managers,
# interpreter shutdown hooks and SQLite connection cleanup.
os._exit(73)
"""
    environment = dict(os.environ)
    existing_pythonpath = environment.get("PYTHONPATH", "")
    environment["PYTHONPATH"] = os.pathsep.join(
        part for part in (str(repository_root), existing_pythonpath) if part
    )

    child = subprocess.run(
        [sys.executable, "-c", child_code, str(database)],
        cwd=repository_root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )

    assert child.returncode == 73, child.stderr

    # Reopen from a distinct process/connection after the writer died without
    # closing SQLite. Both the materialized record and its event journal must
    # be readable and internally consistent.
    with SQLiteLearningMemory(database) as recovered:
        record = recovered.get("crash-recovery.synthetic.paper")
        assert record is not None
        assert record.value == {"samples": 19, "net_edge_bps": 2.4}
        assert record.version == 1
        events = recovered.list_events(key=record.key)
        assert [(event.version, event.event_type, event.status) for event in events] == [
            (1, "put", "testing")
        ]
