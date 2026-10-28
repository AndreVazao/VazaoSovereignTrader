import json
from pathlib import Path

import pytest

from PC_ENGINE.core.canonical_json import canonicalize_json, digest_public_payload


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
