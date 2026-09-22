from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


STATES = ("PLANNED", "APPROVED", "SUBMITTED", "PENDING", "CONFIRMED", "FAILED", "CANCELLED")
TERMINAL_STATES = {"CONFIRMED", "FAILED", "CANCELLED"}
TRANSITIONS = {
    "PLANNED": {"APPROVED", "CANCELLED"},
    "APPROVED": {"SUBMITTED", "CANCELLED"},
    "SUBMITTED": {"PENDING", "FAILED", "CANCELLED"},
    "PENDING": {"CONFIRMED", "FAILED"},
    "CONFIRMED": set(),
    "FAILED": set(),
    "CANCELLED": set(),
}


@dataclass(frozen=True)
class CapitalTransferState:
    intent_id: str
    owner_id: str
    state: str
    updated_at_ms: int
    external_reference: str | None = None
    reason: str | None = None


class CapitalTransferStateStore:
    """Owner-private append-only reconciliation state; never executes transfers."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def _latest(self) -> dict[str, CapitalTransferState]:
        latest: dict[str, CapitalTransferState] = {}
        if not self.path.exists():
            return latest
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    row = json.loads(line)
                    state = CapitalTransferState(**row)
                    latest[state.intent_id] = state
                except (json.JSONDecodeError, TypeError):
                    continue
        return latest

    def record(self, *, intent_id: str, owner_id: str, state: str,
               external_reference: str | None = None, reason: str | None = None) -> CapitalTransferState:
        if not intent_id or not owner_id:
            raise ValueError("intent_id and owner_id are required")
        if state not in STATES:
            raise ValueError("invalid transfer state")
        current = self._latest().get(intent_id)
        if current and current.owner_id != owner_id:
            raise PermissionError("transfer intent belongs to another owner")
        if current and state != current.state and state not in TRANSITIONS[current.state]:
            raise ValueError(f"invalid transition {current.state} -> {state}")
        if current and state == current.state and external_reference == current.external_reference and reason == current.reason:
            return current
        item = CapitalTransferState(intent_id, owner_id, state, int(time.time() * 1000), external_reference, reason)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(item), sort_keys=True) + "\n")
        return item

    def get(self, intent_id: str, owner_id: str) -> CapitalTransferState | None:
        item = self._latest().get(intent_id)
        if item and item.owner_id != owner_id:
            raise PermissionError("transfer intent belongs to another owner")
        return item

    def snapshot(self, owner_id: str | None = None) -> dict[str, Any]:
        rows = self._latest()
        if owner_id is not None:
            rows = {k: v for k, v in rows.items() if v.owner_id == owner_id}
        return {
            "owner_private": True,
            "execution_authority": "NONE",
            "states": list(STATES),
            "terminal_states": sorted(TERMINAL_STATES),
            "intents": [asdict(v) for v in rows.values()],
        }
