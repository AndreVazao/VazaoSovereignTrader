from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from PC_ENGINE.execution.browser_safety import (
    BrowserActionProposal,
    BrowserExecutionSafety,
    BrowserObservation,
    BrowserSafetyStatus,
)
from PC_ENGINE.core.execution_fabric import ExecutionAdapter, ExecutionIntent, ExecutionMethod, ExecutionResult


class BrowserDriver(Protocol):
    def observe(self, intent: ExecutionIntent) -> BrowserObservation:
        ...

    def submit(self, intent: ExecutionIntent, proposal: BrowserActionProposal, observation: BrowserObservation) -> str | None:
        ...

    def verify_exchange(self, intent: ExecutionIntent, external_id: str | None) -> str | None:
        ...


@dataclass
class BrowserExecutionAdapter:
    """ExecutionFabric adapter using observed targets and independent exchange verification."""

    driver: BrowserDriver
    safety: BrowserExecutionSafety
    proposal_factory: callable
    method: ExecutionMethod = ExecutionMethod.BROWSER

    def execute(self, intent: ExecutionIntent) -> ExecutionResult:
        observation = self.driver.observe(intent)
        proposal = self.proposal_factory(intent, observation)
        if not isinstance(proposal, BrowserActionProposal):
            return ExecutionResult(False, "INVALID_BROWSER_PROPOSAL", self.method, reason="proposal must be observed-target action")
        status = self.safety.authorize(observation, proposal)
        if status != BrowserSafetyStatus.READY:
            return ExecutionResult(False, status.value, self.method, reason="browser safety gate")
        external_id = self.driver.submit(intent, proposal, observation)
        exchange_status = self.driver.verify_exchange(intent, external_id)
        verification = self.safety.verify_exchange_outcome(exchange_status=exchange_status, external_id=external_id)
        if verification.status == BrowserSafetyStatus.OUTCOME_UNVERIFIED:
            return ExecutionResult(False, "EXCHANGE_OUTCOME_UNVERIFIED", self.method, external_id=external_id, reason=verification.detail)
        return ExecutionResult(True, verification.detail or "VERIFIED", self.method, external_id=external_id)
