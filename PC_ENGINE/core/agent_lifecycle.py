"""Backend-side creation boundary for persistent agent identity.

This service is an integration seam, not yet wired to the production agent
scheduler/API. The authorizer must be supplied by a trusted backend control
plane; never construct it from client/UI fields.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PC_ENGINE.core.agent_registry import AgentRegistry, AgentRegistryError

Authorizer = Callable[..., str | None]


class AgentCreationDenied(PermissionError):
    """The trusted control plane did not authorize this creation."""


class AgentLifecycle:
    """Authorize, then persist origin; callers cannot choose VST origin."""

    def __init__(self, registry: AgentRegistry, authorize: Authorizer):
        self._registry = registry
        self._authorize = authorize

    def create_vst_agent(
        self,
        *,
        agent_id: str,
        actor_id: str,
        reason: str,
        parent_agent_id: str | None = None,
    ) -> dict[str, Any]:
        """Create an AI-origin agent only after trusted authorization."""
        authorization_id = self._authorize(
            actor_id=actor_id,
            operation="agent.create",
            agent_id=agent_id,
            reason=reason,
        )
        if not isinstance(authorization_id, str) or not authorization_id.strip():
            raise AgentCreationDenied("Agent creation was not authorized")
        try:
            return self._registry.register_created_agent(
                agent_id=agent_id,
                origin_type="vst_created",
                created_by=actor_id,
                reason=reason,
                authorization_id=authorization_id,
                parent_agent_id=parent_agent_id,
            )
        except AgentRegistryError:
            raise

    def create_human_agent(
        self,
        *,
        agent_id: str,
        operator_id: str,
        reason: str,
        parent_agent_id: str | None = None,
    ) -> dict[str, Any]:
        """Register a human-origin agent through the same authorization gate."""
        authorization_id = self._authorize(
            actor_id=operator_id,
            operation="agent.create",
            agent_id=agent_id,
            reason=reason,
        )
        if not isinstance(authorization_id, str) or not authorization_id.strip():
            raise AgentCreationDenied("Agent creation was not authorized")
        return self._registry.register_created_agent(
            agent_id=agent_id,
            origin_type="human_created",
            created_by=operator_id,
            reason=reason,
            authorization_id=authorization_id,
            parent_agent_id=parent_agent_id,
        )
