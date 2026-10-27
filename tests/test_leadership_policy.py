from datetime import datetime, timedelta, timezone

import pytest

from PC_ENGINE.core.leadership_policy import (
    LeadershipDecision,
    LeadershipEvidence,
    evaluate_leadership_request,
)


NOW = datetime(2026, 10, 27, 12, 0, tzinfo=timezone.utc)


def _evidence(**overrides):
    values = {
        "current_epoch": 42,
        "current_lease_expires_at": NOW - timedelta(seconds=1),
        "candidate_installation_id": "pc-2",
        "candidate_approved": True,
        "candidate_healthy": True,
        "checkpoint_is_compatible": True,
        "replication_lag_seconds": 2.0,
        "maximum_replication_lag_seconds": 10.0,
        "coordinator_state_is_consistent": True,
    }
    values.update(overrides)
    return LeadershipEvidence(**values)


def test_approved_healthy_synchronized_candidate_may_request_grant():
    assert evaluate_leadership_request(_evidence(), now=NOW) is LeadershipDecision.ALLOW_REQUEST


def test_last_leader_record_does_not_bypass_unexpired_lease():
    evidence = _evidence(current_lease_expires_at=NOW + timedelta(seconds=30))
    assert evaluate_leadership_request(evidence, now=NOW) is LeadershipDecision.DENY_ACTIVE_LEASE


def test_unapproved_candidate_is_denied():
    assert evaluate_leadership_request(
        _evidence(candidate_approved=False), now=NOW
    ) is LeadershipDecision.DENY_REVOKED_CANDIDATE


def test_unhealthy_candidate_is_denied():
    assert evaluate_leadership_request(
        _evidence(candidate_healthy=False), now=NOW
    ) is LeadershipDecision.DENY_UNHEALTHY_CANDIDATE


@pytest.mark.parametrize(
    "overrides",
    [
        {"checkpoint_is_compatible": False},
        {"replication_lag_seconds": 11.0},
    ],
)
def test_stale_or_incompatible_candidate_is_denied(overrides):
    assert evaluate_leadership_request(
        _evidence(**overrides), now=NOW
    ) is LeadershipDecision.DENY_STALE_STATE


def test_inconsistent_coordinator_state_fails_closed():
    assert evaluate_leadership_request(
        _evidence(coordinator_state_is_consistent=False), now=NOW
    ) is LeadershipDecision.DENY_INVALID_EVIDENCE


def test_naive_datetime_fails_closed():
    evidence = _evidence(current_lease_expires_at=datetime(2026, 10, 27, 11, 0))
    assert evaluate_leadership_request(
        evidence, now=datetime(2026, 10, 27, 12, 0)
    ) is LeadershipDecision.DENY_INVALID_EVIDENCE


def test_negative_replication_lag_fails_closed():
    assert evaluate_leadership_request(
        _evidence(replication_lag_seconds=-1), now=NOW
    ) is LeadershipDecision.DENY_INVALID_EVIDENCE


@pytest.mark.parametrize("invalid_lag", [float("nan"), float("inf"), float("-inf")])
@pytest.mark.parametrize(
    "field",
    ["replication_lag_seconds", "maximum_replication_lag_seconds"],
)
def test_non_finite_replication_lag_fails_closed(field, invalid_lag):
    assert evaluate_leadership_request(
        _evidence(**{field: invalid_lag}), now=NOW
    ) is LeadershipDecision.DENY_INVALID_EVIDENCE


def test_no_prior_lease_can_be_considered_only_with_consistent_evidence():
    assert evaluate_leadership_request(
        _evidence(current_lease_expires_at=None), now=NOW
    ) is LeadershipDecision.ALLOW_REQUEST
