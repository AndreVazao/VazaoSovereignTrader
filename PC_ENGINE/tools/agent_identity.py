"""Fail-closed agent origin and avatar identity policy.

This module is deliberately pure: it does not create agents, persist records, or
render UI. Callers must supply trusted backend provenance, never renderer input.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class OriginType(str, Enum):
    HUMAN_CREATED = "human_created"
    VST_CREATED = "vst_created"
    IMPORTED_VERIFIED = "imported_verified"
    UNKNOWN = "unknown"


class AvatarKind(str, Enum):
    EXISTING = "existing"
    ROBOT = "robot"
    NEUTRAL = "neutral"


@dataclass(frozen=True)
class AgentIdentity:
    agent_id: str
    origin_type: OriginType
    provenance_validated: bool
    persisted: bool = True
    active: bool = True
    quarantined: bool = False
    placeholder: bool = False


def avatar_kind(identity: AgentIdentity) -> AvatarKind:
    """Choose an avatar from trusted identity; unknown/unvalidated stays neutral."""
    if not identity.agent_id.strip() or not identity.provenance_validated:
        return AvatarKind.NEUTRAL
    if identity.origin_type is OriginType.VST_CREATED:
        return AvatarKind.ROBOT
    if identity.origin_type in (OriginType.HUMAN_CREATED, OriginType.IMPORTED_VERIFIED):
        return AvatarKind.EXISTING
    return AvatarKind.NEUTRAL


def growth_metrics(identities: Iterable[AgentIdentity]) -> dict[str, int]:
    """Count persisted, validated records only; never count visual placeholders."""
    rows = [
        row for row in identities
        if row.persisted
        and row.provenance_validated
        and bool(row.agent_id.strip())
        and not row.placeholder
    ]
    return {
        "validated_total": len({row.agent_id for row in rows}),
        "active": len({row.agent_id for row in rows if row.active and not row.quarantined}),
        "quarantined": len({row.agent_id for row in rows if row.quarantined}),
        "inactive": len({row.agent_id for row in rows if not row.active}),
        "placeholders_excluded": sum(1 for row in identities if row.placeholder),
    }
