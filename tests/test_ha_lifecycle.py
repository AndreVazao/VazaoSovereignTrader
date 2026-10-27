import pytest

from PC_ENGINE.core.ha_lifecycle import (
    InvalidMigrationTransition,
    MigrationSnapshot,
    MigrationState,
    is_terminal_migration_state,
    transition_migration,
)


def _snapshot() -> MigrationSnapshot:
    return MigrationSnapshot(
        operation_id="migration-001",
        source_installation_id="install-old",
        destination_installation_id="install-new",
        module_ids=("research", "risk-engine"),
    )


def test_migration_lifecycle_advances_with_monotonic_versions():
    snapshot = _snapshot()
    expected = [
        MigrationState.AUTHORIZED,
        MigrationState.PREPARING,
        MigrationState.STANDBY_SYNCING,
        MigrationState.SOURCE_QUIESCING,
        MigrationState.CHECKPOINTED,
        MigrationState.CUTOVER_PENDING,
        MigrationState.DESTINATION_VERIFYING,
        MigrationState.COMPLETED,
    ]

    for version, target in enumerate(expected):
        snapshot = transition_migration(snapshot, target, expected_version=version)
        assert snapshot.state is target
        assert snapshot.version == version + 1

    assert is_terminal_migration_state(snapshot.state)


def test_migration_rejects_skipping_preparation_and_checkpoint():
    with pytest.raises(InvalidMigrationTransition, match="illegal migration transition"):
        transition_migration(
            _snapshot(),
            MigrationState.COMPLETED,
            expected_version=0,
        )


def test_migration_rejects_stale_expected_version():
    snapshot = transition_migration(
        _snapshot(), MigrationState.AUTHORIZED, expected_version=0
    )
    with pytest.raises(InvalidMigrationTransition, match="stale migration version"):
        transition_migration(
            snapshot, MigrationState.PREPARING, expected_version=0
        )


@pytest.mark.parametrize(
    ("target", "reason"),
    [
        (MigrationState.BLOCKED, ""),
        (MigrationState.FAILED, ""),
    ],
)
def test_failure_terminal_states_require_reason(target, reason):
    with pytest.raises(InvalidMigrationTransition, match="requires a reason_code"):
        transition_migration(
            _snapshot(), target, expected_version=0, reason_code=reason
        )


def test_rollback_requires_checkpoint_and_reason():
    snapshot = _snapshot()
    snapshot = transition_migration(snapshot, MigrationState.AUTHORIZED, expected_version=0)
    snapshot = transition_migration(snapshot, MigrationState.PREPARING, expected_version=1)
    snapshot = transition_migration(snapshot, MigrationState.STANDBY_SYNCING, expected_version=2)
    snapshot = transition_migration(snapshot, MigrationState.SOURCE_QUIESCING, expected_version=3)
    snapshot = transition_migration(snapshot, MigrationState.CHECKPOINTED, expected_version=4)
    snapshot = transition_migration(snapshot, MigrationState.ROLLING_BACK, expected_version=5)

    with pytest.raises(InvalidMigrationTransition, match="requires a reason_code"):
        transition_migration(snapshot, MigrationState.ROLLED_BACK, expected_version=6)

    snapshot = transition_migration(
        snapshot,
        MigrationState.ROLLED_BACK,
        expected_version=6,
        reason_code="destination_health_failed",
    )
    assert snapshot.state is MigrationState.ROLLED_BACK
    assert is_terminal_migration_state(snapshot.state)


def test_migration_rejects_same_source_and_destination():
    snapshot = MigrationSnapshot(
        operation_id="migration-002",
        source_installation_id="same-install",
        destination_installation_id="same-install",
        module_ids=("analysis",),
    )
    with pytest.raises(InvalidMigrationTransition, match="must be different"):
        transition_migration(
            snapshot, MigrationState.AUTHORIZED, expected_version=0
        )


def test_terminal_state_cannot_be_reopened():
    snapshot = transition_migration(
        _snapshot(),
        MigrationState.BLOCKED,
        expected_version=0,
        reason_code="owner_denied",
    )
    with pytest.raises(InvalidMigrationTransition, match="terminal migration state"):
        transition_migration(
            snapshot, MigrationState.AUTHORIZED, expected_version=1
        )
