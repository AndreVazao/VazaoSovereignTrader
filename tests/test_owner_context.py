from pathlib import Path

import pytest

from PC_ENGINE.core.owner_context import OwnerContext


def test_owner_id_is_normalized_and_namespaced(tmp_path: Path):
    context = OwnerContext("Genro_1", tmp_path)
    assert context.owner_id == "genro_1"
    assert context.private_path("runtime_state.json") == tmp_path / "owners" / "genro_1" / "runtime_state.json"


def test_owner_id_rejects_path_traversal(tmp_path: Path):
    with pytest.raises(ValueError):
        OwnerContext("../andre", tmp_path)


def test_private_path_cannot_escape_namespace(tmp_path: Path):
    context = OwnerContext("andre", tmp_path)
    with pytest.raises(ValueError):
        context.private_path("../../outside.json")


def test_owner_context_is_independent_per_owner(tmp_path: Path):
    andre = OwnerContext("andre", tmp_path)
    genro = OwnerContext("genro", tmp_path)
    assert andre.private_root != genro.private_root
    assert andre.private_path("runtime_state.json") != genro.private_path("runtime_state.json")
