import pytest

from PC_ENGINE.core.agent_registry import AgentRegistry, AgentRegistryError


def create(registry, agent_id="agent-1", origin="vst_created", created_by="vst-ceo"):
    return registry.register_created_agent(
        agent_id=agent_id,
        origin_type=origin,
        created_by=created_by,
        reason="approved expansion task",
        authorization_id="auth-123",
    )


def test_registry_persists_origin_and_creation_provenance(tmp_path):
    path = tmp_path / "agents.json"
    first = AgentRegistry(path)
    record = create(first)
    reloaded = AgentRegistry(path).get("agent-1")
    assert reloaded["origin_type"] == "vst_created"
    assert reloaded["provenance_validated"] is True
    assert reloaded["authorization_id"] == "auth-123"
    assert reloaded["creation_event_sha256"] == record["creation_event_sha256"]


def test_duplicate_creation_is_idempotent_but_conflicting_origin_fails(tmp_path):
    registry = AgentRegistry(tmp_path / "agents.json")
    first = create(registry)
    assert create(registry) == first
    with pytest.raises(AgentRegistryError):
        create(registry, origin="human_created")


def test_new_agent_creation_rejects_unknown_or_imported_origin(tmp_path):
    registry = AgentRegistry(tmp_path / "agents.json")
    with pytest.raises(AgentRegistryError):
        create(registry, origin="unknown")
    with pytest.raises(AgentRegistryError):
        registry.register_created_agent(
            agent_id="agent-2", origin_type="human_created", created_by="human",
            reason="initial setup", authorization_id="",
        )


def test_restore_is_idempotent_and_conflicting_record_is_rejected(tmp_path):
    registry = AgentRegistry(tmp_path / "agents.json")
    record = create(registry)
    restored = AgentRegistry(tmp_path / "restored.json")
    assert restored.import_verified_record(record) == record
    assert restored.import_verified_record(record) == record
    conflicting = dict(record, creation_event_sha256="0" * 64)
    with pytest.raises(AgentRegistryError):
        restored.import_verified_record(conflicting)


def test_restore_rejects_tampered_origin_even_if_hash_field_is_present(tmp_path):
    record = create(AgentRegistry(tmp_path / "source.json"))
    record["origin_type"] = "human_created"
    with pytest.raises(AgentRegistryError):
        AgentRegistry(tmp_path / "target.json").import_verified_record(record)


def test_registry_refuses_to_overwrite_corrupt_file(tmp_path):
    path = tmp_path / "agents.json"
    path.write_text("{broken", encoding="utf-8")
    registry = AgentRegistry(path)
    with pytest.raises(AgentRegistryError):
        create(registry)
    assert path.read_text(encoding="utf-8") == "{broken"


def test_status_changes_do_not_change_identity_origin(tmp_path):
    registry = AgentRegistry(tmp_path / "agents.json")
    create(registry)
    registry.set_status("agent-1", "quarantined")
    loaded = registry.get("agent-1")
    assert loaded["origin_type"] == "vst_created"
    assert loaded["status"] == "quarantined"
