from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from .shared_intelligence import SharedIntelligenceImporter, SharedIntelligenceStore


class SharedIntelligenceProvider(Protocol):
    """Cloud transport contract. Providers must exchange public artifacts only."""

    def pull(self, *, cursor: str | None, limit: int) -> dict[str, Any]: ...
    def push(self, *, rows: list[dict[str, Any]]) -> dict[str, Any]: ...


@dataclass(frozen=True)
class SharedSyncState:
    cursor: str = ""
    last_pull_ms: int = 0
    last_push_ms: int = 0
    last_bootstrap_ms: int = 0


class SharedIntelligenceSync:
    """Continuous best-effort sync; local trading never depends on the provider."""

    def __init__(self, store: SharedIntelligenceStore, state_path: str | Path, *, pull_limit: int = 500):
        self.store = store
        self.state_path = Path(state_path)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.pull_limit = max(1, int(pull_limit))

    def _read_state(self) -> SharedSyncState:
        if not self.state_path.exists():
            return SharedSyncState()
        import json
        raw = json.loads(self.state_path.read_text(encoding="utf-8"))
        return SharedSyncState(
            cursor=str(raw.get("cursor", "")),
            last_pull_ms=int(raw.get("last_pull_ms", 0)),
            last_push_ms=int(raw.get("last_push_ms", 0)),
            last_bootstrap_ms=int(raw.get("last_bootstrap_ms", 0)),
        )

    def _write_state(self, state: SharedSyncState) -> None:
        import json
        tmp = self.state_path.with_suffix(self.state_path.suffix + ".tmp")
        tmp.write_text(json.dumps(state.__dict__, sort_keys=True), encoding="utf-8")
        tmp.replace(self.state_path)

    def bootstrap(self, provider: SharedIntelligenceProvider, *, now_ms: int | None = None) -> dict[str, int]:
        """Download the current shared intelligence snapshot for a new machine/login."""
        return self.sync_once(provider, now_ms=now_ms, bootstrap=True)

    def sync_once(self, provider: SharedIntelligenceProvider, *, now_ms: int | None = None, bootstrap: bool = False) -> dict[str, int]:
        now_ms = int(now_ms if now_ms is not None else time.time() * 1000)
        state = self._read_state()
        cursor = None if bootstrap else (state.cursor or None)
        try:
            response = provider.pull(cursor=cursor, limit=self.pull_limit)
            rows = response.get("rows", []) if isinstance(response, dict) else []
            result = SharedIntelligenceImporter(self.store).import_rows(rows, now_ms=now_ms)
            next_cursor = str(response.get("next_cursor", state.cursor)) if isinstance(response, dict) else state.cursor
            self._write_state(SharedSyncState(
                cursor=next_cursor,
                last_pull_ms=now_ms,
                last_push_ms=state.last_push_ms,
                last_bootstrap_ms=now_ms if bootstrap else state.last_bootstrap_ms,
            ))
            return {"accepted": result.accepted, "rejected": result.rejected, "skipped": result.skipped}
        except Exception:
            # Cloud/sync failure is isolated from the trader. Existing local knowledge remains usable.
            return {"accepted": 0, "rejected": 0, "skipped": 0}

    def push_new(self, provider: SharedIntelligenceProvider, *, now_ms: int | None = None) -> dict[str, int]:
        now_ms = int(now_ms if now_ms is not None else time.time() * 1000)
        state = self._read_state()
        rows = self.store.read()
        try:
            response = provider.push(rows=rows)
            self._write_state(SharedSyncState(
                cursor=str(response.get("next_cursor", state.cursor)) if isinstance(response, dict) else state.cursor,
                last_pull_ms=state.last_pull_ms,
                last_push_ms=now_ms,
                last_bootstrap_ms=state.last_bootstrap_ms,
            ))
            return {"uploaded": int(response.get("accepted", len(rows))) if isinstance(response, dict) else len(rows)}
        except Exception:
            return {"uploaded": 0}
