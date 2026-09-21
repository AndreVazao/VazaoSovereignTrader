from __future__ import annotations

import os
import re
from pathlib import Path


_OWNER_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


class OwnerContext:
    """Immutable identity and private storage boundary for one trader owner.

    Shared market intelligence is intentionally outside this boundary. Financial
    state, execution state, logs and credentials-related runtime state must live
    under the owner's private namespace.
    """

    def __init__(self, owner_id: str, runtime_root: Path):
        normalized = self.normalize_owner_id(owner_id)
        self.owner_id = normalized
        self.runtime_root = Path(runtime_root).resolve()
        self.private_root = (self.runtime_root / "owners" / normalized).resolve()
        self.private_root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def normalize_owner_id(owner_id: str) -> str:
        value = str(owner_id or "").strip().lower()
        if not _OWNER_RE.fullmatch(value):
            raise ValueError("invalid owner_id")
        return value

    @classmethod
    def from_config(cls, config: dict, runtime_root: Path) -> "OwnerContext":
        owner_cfg = config.get("owner", {}) if isinstance(config, dict) else {}
        configured = str(owner_cfg.get("id", "")).strip()
        owner_id = os.getenv("VST_OWNER_ID", configured or "andre")
        return cls(owner_id, runtime_root)

    def private_path(self, relative: str | Path) -> Path:
        candidate = (self.private_root / Path(relative)).resolve()
        if candidate != self.private_root and self.private_root not in candidate.parents:
            raise ValueError("owner path escapes private namespace")
        candidate.parent.mkdir(parents=True, exist_ok=True)
        return candidate

    def snapshot(self) -> dict:
        return {
            "owner_id": self.owner_id,
            "private_namespace": f"owners/{self.owner_id}",
        }
