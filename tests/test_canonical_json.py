import base64
import hashlib
import json
from pathlib import Path

import pytest

from PC_ENGINE.core.canonical_json import (
    canonicalize_json,
    canonicalize_provenance_message,
    digest_public_payload,
)


FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "cloud"
    / "shared-learning"
    / "tests"
    / "fixtures"
    / "canonical-json-vectors.json"
)


def test_python_rfc8785_matches_shared_typescript_golden_vectors():
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert fixture["format"] == "RFC8785-JCS"
    for vector in fixture["vectors"]:
        canonical = canonicalize_json(vector["input"])
        assert canonical.decode("utf-8") == vector["canonical"], vector["name"]
        assert digest_public_payload(vector["input"]) == vector["sha256"], vector["name"]


@pytest.mark.parametrize(
    "value",
    [
        float("nan"),
        float("inf"),
        {"nested": float("-inf")},
        {"bad": object()},
        {"bad": {1, 2}},
    ],
)
def test_python_canonicalization_rejects_values_outside_json_domain(value):
    with pytest.raises(ValueError, match="invalid_jcs_value"):
        canonicalize_json(value)


def test_python_provenance_message_uses_the_same_sorted_signed_fields():
    envelope = {
        "schema_version": 1,
        "organization_id": "123e4567-e89b-42d3-a456-426614174000",
        "installation_id": "223e4567-e89b-42d3-a456-426614174000",
        "agent_id": "323e4567-e89b-42d3-a456-426614174000",
        "department_id": "423e4567-e89b-42d3-a456-426614174000",
        "artifact_id": "artifact-golden-001",
        "payload_digest": "a" * 64,
        "created_at_ms": 1793164800000,
        "producer_version": "0.1.0",
        "source_artifact_ids": ["root-001", "root-002"],
        "signature": "must-not-be-signed",
    }
    expected = (
        '{"agent_id":"323e4567-e89b-42d3-a456-426614174000",'
        '"artifact_id":"artifact-golden-001","created_at_ms":1793164800000,'
        '"department_id":"423e4567-e89b-42d3-a456-426614174000",'
        '"installation_id":"223e4567-e89b-42d3-a456-426614174000",'
        '"organization_id":"123e4567-e89b-42d3-a456-426614174000",'
        '"payload_digest":"' + ("a" * 64) + '","producer_version":"0.1.0",'
        '"schema_version":1,"source_artifact_ids":["root-001","root-002"]}'
    )
    assert canonicalize_provenance_message(envelope).decode("utf-8") == expected


def test_python_verifies_shared_typescript_ed25519_provenance_vector():
    from cryptography.hazmat.primitives.serialization import load_der_public_key

    vector_path = (
        Path(__file__).resolve().parents[1]
        / "cloud"
        / "shared-learning"
        / "tests"
        / "fixtures"
        / "provenance-ed25519-vector.json"
    )
    fixture = json.loads(vector_path.read_text(encoding="utf-8"))
    message = canonicalize_provenance_message(fixture["envelope"])
    assert message.decode("utf-8") == fixture["message"]
    assert hashlib.sha256(message).hexdigest() == fixture["message_sha256"]

    public_key = load_der_public_key(
        base64.b64decode(fixture["public_key_spki_der_base64"])
    )
    signature = base64.urlsafe_b64decode(
        fixture["signature_base64url"]
        + "=" * (-len(fixture["signature_base64url"]) % 4)
    )
    public_key.verify(signature, message)


@pytest.mark.parametrize("value", [{"value": "\ud800"}, {"\udfff": 1}])
def test_python_canonicalization_rejects_unpaired_unicode_surrogates(value):
    with pytest.raises(ValueError, match="invalid_jcs_value"):
        canonicalize_json(value)
