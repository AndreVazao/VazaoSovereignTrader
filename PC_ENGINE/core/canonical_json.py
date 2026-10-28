"""RFC 8785/JCS canonicalization for public shared-learning payloads.

This module is a serialization primitive only. It does not authorize an artifact,
register a device, or enable signing by itself.
"""
from __future__ import annotations

import hashlib
from typing import Any

import rfc8785


def canonicalize_json(value: Any) -> bytes:
    """Return RFC 8785 canonical JSON as UTF-8 bytes; reject unsupported values."""
    try:
        encoded = rfc8785.dumps(value)
    except Exception as exc:
        raise ValueError("invalid_jcs_value") from exc
    if not isinstance(encoded, bytes):
        raise TypeError("rfc8785_did_not_return_bytes")
    return encoded


def digest_public_payload(value: Any) -> str:
    """SHA-256 of the exact canonical UTF-8 representation, lowercase hex."""
    return hashlib.sha256(canonicalize_json(value)).hexdigest()


def canonicalize_provenance_message(envelope: dict[str, Any]) -> bytes:
    """Build the signed v1 provenance message using the TypeScript field contract."""
    signed = {
        "schema_version": envelope["schema_version"],
        "organization_id": envelope["organization_id"].lower(),
        "installation_id": envelope["installation_id"].lower(),
        "agent_id": envelope["agent_id"].lower(),
        "department_id": envelope["department_id"].lower(),
        "artifact_id": envelope["artifact_id"],
        "payload_digest": envelope["payload_digest"].lower(),
        "created_at_ms": envelope["created_at_ms"],
        "producer_version": envelope["producer_version"],
        "source_artifact_ids": list(envelope["source_artifact_ids"]),
    }
    return canonicalize_json(signed)
