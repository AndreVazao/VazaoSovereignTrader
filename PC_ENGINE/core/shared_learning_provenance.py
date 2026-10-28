"""Client-side Ed25519 signing for explicitly enabled shared-learning provenance.

Private keys are injected by the caller and held only in memory. This module does
not enroll an installation, approve a key, or enable cloud publication by itself.
"""
from __future__ import annotations

import base64
import re
import time
from typing import Any, Sequence

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from PC_ENGINE.core.canonical_json import canonicalize_provenance_message, digest_public_payload


_UUID = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


class VerifiedProvenanceSigner:
    """Sign v1 provenance envelopes using an enrolled installation's Ed25519 key.

    The caller must obtain the key and immutable identity IDs from a trusted local
    configuration/secret provider. The server independently checks enrollment,
    approval, membership, key fingerprint, payload digest and signature.
    """

    def __init__(
        self,
        *,
        organization_id: str,
        installation_id: str,
        agent_id: str,
        department_id: str,
        private_key_pem: bytes,
        password: bytes | None = None,
    ) -> None:
        self.organization_id = self._uuid(organization_id, "organization_id")
        self.installation_id = self._uuid(installation_id, "installation_id")
        self.agent_id = self._uuid(agent_id, "agent_id")
        self.department_id = self._uuid(department_id, "department_id")
        if not isinstance(private_key_pem, bytes) or not private_key_pem:
            raise ValueError("provenance_private_key_required")
        try:
            key = serialization.load_pem_private_key(private_key_pem, password=password)
        except (TypeError, ValueError) as exc:
            raise ValueError("provenance_private_key_invalid") from exc
        if not isinstance(key, Ed25519PrivateKey):
            raise ValueError("provenance_requires_ed25519_private_key")
        self._private_key = key

    @staticmethod
    def _uuid(value: str, field: str) -> str:
        if not isinstance(value, str) or not _UUID.fullmatch(value):
            raise ValueError("invalid_provenance_" + field)
        return value.lower()

    def sign(
        self,
        public_payload: dict[str, Any],
        *,
        source_artifact_ids: Sequence[str],
    ) -> dict[str, Any]:
        if not isinstance(public_payload, dict):
            raise ValueError("provenance_payload_must_be_object")
        artifact_id = public_payload.get("artifact_id")
        producer_version = public_payload.get("producer_version")
        if (
            not isinstance(artifact_id, str)
            or not artifact_id
            or artifact_id.strip() != artifact_id
            or len(artifact_id) > 128
        ):
            raise ValueError("invalid_provenance_artifact_id")
        if (
            not isinstance(producer_version, str)
            or not producer_version
            or producer_version.strip() != producer_version
            or len(producer_version) > 64
        ):
            raise ValueError("invalid_provenance_producer_version")
        if isinstance(source_artifact_ids, (str, bytes)) or not isinstance(source_artifact_ids, Sequence):
            raise ValueError("invalid_provenance_lineage")
        sources = list(source_artifact_ids)
        if (
            len(sources) > 32
            or any(
                not isinstance(item, str)
                or not item
                or item.strip() != item
                or len(item) > 128
                for item in sources
            )
            or len(set(sources)) != len(sources)
            or artifact_id in sources
        ):
            raise ValueError("invalid_provenance_lineage")

        envelope: dict[str, Any] = {
            "schema_version": 1,
            "organization_id": self.organization_id,
            "installation_id": self.installation_id,
            "agent_id": self.agent_id,
            "department_id": self.department_id,
            "artifact_id": artifact_id,
            "payload_digest": digest_public_payload(public_payload),
            "created_at_ms": time.time_ns() // 1_000_000,
            "producer_version": producer_version,
            "source_artifact_ids": sources,
            "signature": "",
        }
        message = canonicalize_provenance_message(envelope)
        signature = self._private_key.sign(message)
        envelope["signature"] = base64.urlsafe_b64encode(signature).rstrip(b"=").decode("ascii")
        return envelope
