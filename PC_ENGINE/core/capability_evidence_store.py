from __future__ import annotations

import json
import os
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterable

from PC_ENGINE.core.runtime_capability_probe import RuntimeProbeResult


class CapabilityEvidenceStore:
    """Durable, append-only audit trail for capability verification evidence."""

    SCHEMA_VERSION = 1

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def record(
        self,
        result: RuntimeProbeResult,
        *,
        observed_at_ms: int | None = None,
    ) -> dict[str, Any]:
        observed = int(observed_at_ms or time.time() * 1000)
        row = {
            "schema_version": self.SCHEMA_VERSION,
            "observed_at_ms": observed,
            **asdict(result),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(line)
            handle.flush()
            os.fsync(handle.fileno())
        return row

    def load(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        rows: list[dict[str, Any]] = []
        try:
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(row, dict) and row.get("schema_version") == self.SCHEMA_VERSION:
                    rows.append(row)
        except OSError:
            return []
        return rows

    def latest(
        self,
        *,
        venue: str,
        capability: str,
        environment: str,
    ) -> dict[str, Any] | None:
        env = str(environment).upper()
        matches = [
            row
            for row in self.load()
            if str(row.get("venue")) == str(venue)
            and str(row.get("capability")) == str(capability)
            and str(row.get("environment")).upper() == env
        ]
        return max(matches, key=lambda row: int(row.get("observed_at_ms", 0) or 0), default=None)

    def snapshot(self) -> list[dict[str, Any]]:
        return list(self.load())
