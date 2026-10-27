"""Pure policy checks for requesting a new VST leadership lease.

This is a local policy helper, not a distributed lock or authority source.
A durable coordinator must atomically allocate epochs and issue authenticated grants.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from math import isfinite


class LeadershipDecision(str, Enum):
    ALLOW_REQUEST = "allow_request"
    DENY_ACTIVE_LEASE = "deny_active_lease"
    DENY_REVOKED_CANDIDATE = "deny_revoked_candidate"
    DENY_UNHEALTHY_CANDIDATE = "deny_unhealthy_candidate"
    DENY_STALE_STATE = "deny_stale_state"
    DENY_INVALID_EVIDENCE = "deny_invalid_evidence"


@dataclass(frozen=True)
class LeadershipEvidence:
    current_epoch: int
    current_lease_expires_at: datetime | None
    candidate_installation_id: str
    candidate_approved: bool
    candidate_healthy: bool
    checkpoint_is_compatible: bool
    replication_lag_seconds: float
    maximum_replication_lag_seconds: float
    coordinator_state_is_consistent: bool


def evaluate_leadership_request(
    evidence: LeadershipEvidence,
    *,
    now: datetime,
) -> LeadershipDecision:
    """Evaluate whether a candidate may request a grant; never issues a grant.

    The caller must obtain a new epoch through an authenticated, durable,
    atomic coordinator transaction. Local clocks are not authoritative.
    """
    if not evidence.candidate_installation_id.strip() or evidence.current_epoch < 0:
        return LeadershipDecision.DENY_INVALID_EVIDENCE
    if (
        not isfinite(evidence.replication_lag_seconds)
        or not isfinite(evidence.maximum_replication_lag_seconds)
        or evidence.replication_lag_seconds < 0
        or evidence.maximum_replication_lag_seconds < 0
    ):
        return LeadershipDecision.DENY_INVALID_EVIDENCE
    if not evidence.coordinator_state_is_consistent:
        return LeadershipDecision.DENY_INVALID_EVIDENCE
    if evidence.current_lease_expires_at is not None:
        expiry = evidence.current_lease_expires_at
        if expiry.tzinfo is None or now.tzinfo is None:
            return LeadershipDecision.DENY_INVALID_EVIDENCE
        if now < expiry:
            return LeadershipDecision.DENY_ACTIVE_LEASE
    if not evidence.candidate_approved:
        return LeadershipDecision.DENY_REVOKED_CANDIDATE
    if not evidence.candidate_healthy:
        return LeadershipDecision.DENY_UNHEALTHY_CANDIDATE
    if not evidence.checkpoint_is_compatible or (
        evidence.replication_lag_seconds > evidence.maximum_replication_lag_seconds
    ):
        return LeadershipDecision.DENY_STALE_STATE
    return LeadershipDecision.ALLOW_REQUEST
