from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from PC_ENGINE.execution.browser_safety import (
    BrowserActionProposal,
    BrowserExecutionSafety,
    BrowserObservation,
    BrowserSafetyStatus,
)
from PC_ENGINE.execution.browser_execution_ledger import BrowserExecutionLedger
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
    """Observed-target browser execution with durable duplicate protection."""

    driver: BrowserDriver
    safety: BrowserExecutionSafety
    proposal_factory: callable
    ledger: BrowserExecutionLedger | None = None
    method: ExecutionMethod = ExecutionMethod.BROWSER

    def execute(self, intent: ExecutionIntent) -> ExecutionResult:
        if self.ledger is not None:
            previous = self.ledger.latest(intent.idempotency_key)
            if previous is not None:
                if previous.state == "VERIFIED":
                    return ExecutionResult(True, "VERIFIED", self.method, external_id=previous.external_id)
                if previous.state in {"SUBMITTED", "PARTIAL", "REJECTED"}:
                    return ExecutionResult(False, "RECOVER_EXISTING_BROWSER_SUBMISSION", self.method, external_id=previous.external_id, reason="durable browser submission already exists")

        observation = self.driver.observe(intent)
        proposal = self.proposal_factory(intent, observation)
        if not isinstance(proposal, BrowserActionProposal):
            return ExecutionResult(False, "INVALID_BROWSER_PROPOSAL", self.method, reason="proposal must be observed-target action")
        status = self.safety.authorize(observation, proposal)
        if status != BrowserSafetyStatus.READY:
            return ExecutionResult(False, status.value, self.method, reason="browser safety gate")

        if self.ledger is not None:
            self.ledger.append(
                intent=intent,
                state="SUBMISSION_AUTHORIZED",
                external_id=None,
                page_fingerprint=observation.page_fingerprint,
                context_fingerprint=observation.context_fingerprint,
            )

        external_id = self.driver.submit(intent, proposal, observation)
        if self.ledger is not None:
            self.ledger.append(
                intent=intent,
                state="SUBMITTED",
                external_id=external_id,
                page_fingerprint=observation.page_fingerprint,
                context_fingerprint=observation.context_fingerprint,
            )

        exchange_status = self.driver.verify_exchange(intent, external_id)
        verification = self.safety.verify_exchange_outcome(exchange_status=exchange_status, external_id=external_id)
        if verification.status == BrowserSafetyStatus.OUTCOME_UNVERIFIED:
            return ExecutionResult(False, "EXCHANGE_OUTCOME_UNVERIFIED", self.method, external_id=external_id, reason=verification.detail)

        final_state = "VERIFIED" if verification.status == BrowserSafetyStatus.READY else str(exchange_status or "REJECTED").upper()
        if self.ledger is not None:
            self.ledger.append(
                intent=intent,
                state=final_state,
                external_id=external_id,
                page_fingerprint=observation.page_fingerprint,
                context_fingerprint=observation.context_fingerprint,
            )
        return ExecutionResult(True, verification.detail or "VERIFIED", self.method, external_id=external_id)
