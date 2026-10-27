"""Pure, fail-closed lifecycle model for planned module migration.

This module validates migration progress only. It does not perform network I/O,
elect leaders, grant authority, move files, or authorize exchange actions.
Runtime integration must use authenticated fencing/lease enforcement separately.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class MigrationState(str, Enum):
    REQUESTED = "requested"
    AUTHORIZED = "authorized"
    PREPARING = "preparing"
    STANDBY_SYNCING = "standby_syncing"
    SOURCE_QUIESCING = "source_quiescing"
    CHECKPOINTED = "checkpointed"
    CUTOVER_PENDING = "cutover_pending"
    DESTINATION_VERIFYING = "destination_verifying"
    COMPLETED = "completed"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"
    BLOCKED = "blocked"
    FAILED = "failed"


_TERMINAL = {
    MigrationState.COMPLETED,
    MigrationState.ROLLED_BACK,
    MigrationState.BLOCKED,
    MigrationState.FAILED,
}

_ALLOWED: dict[MigrationState, frozenset[MigrationState]] = {
    MigrationState.REQUESTED: frozenset({MigrationState.AUTHORIZED, MigrationState.BLOCKED, MigrationState.FAILED}),
    MigrationState.AUTHORIZED: frozenset({MigrationState.PREPARING, MigrationState.BLOCKED, MigrationState.FAILED}),
    MigrationState.PREPARING: frozenset({MigrationState.STANDBY_SYNCING, MigrationState.BLOCKED, MigrationState.FAILED}),
    MigrationState.STANDBY_SYNCING: frozenset({MigrationState.SOURCE_QUIESCING, MigrationState.BLOCKED, MigrationState.FAILED}),
    MigrationState.SOURCE_QUIESCING: frozenset({MigrationState.CHECKPOINTED, MigrationState.ROLLING_BACK, MigrationState.FAILED}),
    MigrationState.CHECKPOINTED: frozenset({MigrationState.CUTOVER_PENDING, MigrationState.ROLLING_BACK, MigrationState.FAILED}),
    MigrationState.CUTOVER_PENDING: frozenset({MigrationState.DESTINATION_VERIFYING, MigrationState.ROLLING_BACK, MigrationState.FAILED}),
    MigrationState.DESTINATION_VERIFYING: frozenset({MigrationState.COMPLETED, MigrationState.ROLLING_BACK, MigrationState.FAILED}),
    MigrationState.ROLLING_BACK: frozenset({MigrationState.ROLLED_BACK, MigrationState.FAILED}),
    MigrationState.COMPLETED: frozenset(),
    MigrationState.ROLLED_BACK: frozenset(),
    MigrationState.BLOCKED: frozenset(),
    MigrationState.FAILED: frozenset(),
}


@dataclass(frozen=True)
class MigrationSnapshot:
    operation_id: str
    source_installation_id: str
    destination_installation_id: str
    module_ids: tuple[str, ...]
    state: MigrationState = MigrationState.REQUESTED
    version: int = 0
    reason_code: str = ""


class InvalidMigrationTransition(ValueError):
    """Raised when a migration attempts an illegal or stale transition."""


def transition_migration(
    snapshot: MigrationSnapshot,
    target: MigrationState,
    *,
    expected_version: int,
    reason_code: str = "",
) -> MigrationSnapshot:
    """Return the next immutable snapshot, rejecting stale or illegal changes."""
    if snapshot.version != expected_version:
        raise InvalidMigrationTransition(
            f"stale migration version: expected {expected_version}, current {snapshot.version}"
        )
    if not snapshot.operation_id.strip():
        raise InvalidMigrationTransition("operation_id must be non-empty")
    if not snapshot.source_installation_id.strip() or not snapshot.destination_installation_id.strip():
        raise InvalidMigrationTransition("source and destination installation IDs are required")
    if snapshot.source_installation_id == snapshot.destination_installation_id:
        raise InvalidMigrationTransition("source and destination must be different installations")
    if not snapshot.module_ids or any(not module_id.strip() for module_id in snapshot.module_ids):
        raise InvalidMigrationTransition("at least one non-empty module ID is required")
    if snapshot.state in _TERMINAL:
        raise InvalidMigrationTransition(f"terminal migration state: {snapshot.state.value}")
    if target not in _ALLOWED[snapshot.state]:
        raise InvalidMigrationTransition(
            f"illegal migration transition: {snapshot.state.value} -> {target.value}"
        )
    if target in {MigrationState.BLOCKED, MigrationState.FAILED, MigrationState.ROLLED_BACK} and not reason_code.strip():
        raise InvalidMigrationTransition(f"{target.value} requires a reason_code")
    return MigrationSnapshot(
        operation_id=snapshot.operation_id,
        source_installation_id=snapshot.source_installation_id,
        destination_installation_id=snapshot.destination_installation_id,
        module_ids=snapshot.module_ids,
        state=target,
        version=snapshot.version + 1,
        reason_code=reason_code.strip(),
    )


def is_terminal_migration_state(state: MigrationState) -> bool:
    """Return whether a migration state accepts no further transitions."""
    return state in _TERMINAL
