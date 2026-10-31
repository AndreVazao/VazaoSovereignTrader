"""Small persistent agent identity registry.

This module is backend-side infrastructure. UI payloads must never be passed as
trusted origin metadata. The caller is responsible for authenticating/authorizing
creation before invoking register_created_agent().
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
ORIGINS = {"human_created", "vst_created", "imported_verified", "unknown"}
STATUSES = {"active", "training", "quarantined", "suspended", "deactivated"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class AgentRegistryError(ValueError):
    """Invalid or inconsistent agent registry operation."""


class AgentRegistry:
    """Atomic JSON registry with stable IDs and idempotent restore/import."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"schema_version": SCHEMA_VERSION, "agents": {}}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise AgentRegistryError("Agent registry unreadable; refusing to overwrite") from exc
        if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION:
            raise AgentRegistryError("Unsupported agent registry schema")
        agents = data.get("agents")
        if not isinstance(agents, dict):
            raise AgentRegistryError("Invalid agent registry structure")
        return data

    def _write(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=self.path.name + ".", suffix=".tmp", dir=str(self.path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(data, stream, ensure_ascii=False, sort_keys=True, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_name, self.path)
        finally:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass

    def register_created_agent(
        self,
        *,
        agent_id: str,
        origin_type: str,
        created_by: str,
        reason: str,
        authorization_id: str,
        parent_agent_id: str | None = None,
    ) -> dict[str, Any]:
        """Persist a new agent after backend authorization has already succeeded."""
        if not agent_id.strip() or not created_by.strip() or not reason.strip() or not authorization_id.strip():
            raise AgentRegistryError("agent_id, created_by, reason and authorization_id are required")
        if origin_type not in {"human_created", "vst_created"}:
            raise AgentRegistryError("New agent creation must specify human_created or vst_created")
        data = self._read()
        agents = data["agents"]
        if agent_id in agents:
            existing = agents[agent_id]
            if existing.get("origin_type") != origin_type or existing.get("created_by") != created_by:
                raise AgentRegistryError("Agent ID already exists with conflicting provenance")
            return dict(existing)
        record: dict[str, Any] = {
            "agent_id": agent_id,
            "origin_type": origin_type,
            "created_by": created_by,
            "created_at": _utc_now(),
            "schema_version": SCHEMA_VERSION,
            "reason": reason,
            "authorization_id": authorization_id,
            "parent_agent_id": parent_agent_id,
            "provenance_validated": True,
            "status": "active",
        }
        record["creation_event_sha256"] = _canonical_hash(record)
        agents[agent_id] = record
        self._write(data)
        return dict(record)

    def import_verified_record(self, record: dict[str, Any]) -> dict[str, Any]:
        """Restore an existing validated record idempotently; never mint a new ID."""
        agent_id = str(record.get("agent_id", "")).strip()
        origin = record.get("origin_type")
        if not agent_id or origin not in ORIGINS:
            raise AgentRegistryError("Imported record requires agent_id and a recognized origin")
        if not record.get("provenance_validated") or not record.get("creation_event_sha256"):
            raise AgentRegistryError("Imported record has no validated creation provenance")
        data = self._read()
        agents = data["agents"]
        existing = agents.get(agent_id)
        if existing is not None:
            if existing.get("creation_event_sha256") != record.get("creation_event_sha256"):
                raise AgentRegistryError("Conflicting restore record for existing agent ID")
            return dict(existing)
        clean = dict(record)
        clean["schema_version"] = SCHEMA_VERSION
        clean["status"] = clean.get("status", "active") if clean.get("status", "active") in STATUSES else "suspended"
        agents[agent_id] = clean
        self._write(data)
        return dict(clean)

    def get(self, agent_id: str) -> dict[str, Any] | None:
        record = self._read()["agents"].get(agent_id)
        return dict(record) if record is not None else None

    def list_agents(self) -> list[dict[str, Any]]:
        return [dict(record) for record in self._read()["agents"].values()]

    def set_status(self, agent_id: str, status: str) -> dict[str, Any]:
        if status not in STATUSES:
            raise AgentRegistryError("Unsupported agent status")
        data = self._read()
        record = data["agents"].get(agent_id)
        if record is None:
            raise AgentRegistryError("Unknown agent ID")
        record["status"] = status
        self._write(data)
        return dict(record)
