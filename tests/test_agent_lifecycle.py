import pytest

from PC_ENGINE.core.agent_lifecycle import AgentCreationDenied, AgentLifecycle
from PC_ENGINE.core.agent_registry import AgentRegistry


def test_vst_creation_origin_is_fixed_by_backend_service(tmp_path):
    seen = []

    def authorize(**request):
        seen.append(request)
        return "approved-task-44"

    lifecycle = AgentLifecycle(AgentRegistry(tmp_path / "agents.json"), authorize)
    record = lifecycle.create_vst_agent(
        agent_id="robot-01", actor_id="vst-ceo", reason="approved expansion"
    )
    assert record["origin_type"] == "vst_created"
    assert record["authorization_id"] == "approved-task-44"
    assert seen == [{
        "actor_id": "vst-ceo",
        "operation": "agent.create",
        "agent_id": "robot-01",
        "reason": "approved expansion",
    }]


def test_creation_fails_closed_when_authorizer_denies(tmp_path):
    lifecycle = AgentLifecycle(
        AgentRegistry(tmp_path / "agents.json"),
        lambda **request: None,
    )
    with pytest.raises(AgentCreationDenied):
        lifecycle.create_vst_agent(
            agent_id="robot-02", actor_id="vst-ceo", reason="no approval"
        )
    assert AgentRegistry(tmp_path / "agents.json").list_agents() == []


def test_human_creation_preserves_human_origin(tmp_path):
    lifecycle = AgentLifecycle(
        AgentRegistry(tmp_path / "agents.json"),
        lambda **request: "operator-approval-9",
    )
    record = lifecycle.create_human_agent(
        agent_id="human-01", operator_id="operator-1", reason="initial setup"
    )
    assert record["origin_type"] == "human_created"
