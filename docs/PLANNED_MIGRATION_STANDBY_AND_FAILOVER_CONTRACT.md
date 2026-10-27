# Planned Migration, Standby and Failover Contract

**Status:** architecture contract for staged implementation; not yet implemented end-to-end.
**Scope:** Vazão Sovereign Trader only. DGM-MAT is a separate system.
**Safety:** PAPER/read-only during development. This design does not authorize live trading, transfers or withdrawals.

## Goals

VST must support a controlled move of departments between authorized computers while preserving a recoverable standby copy. The virtual office must depict actual service state and migration progress, not substitute animation for real operations.

Required capabilities:
- One common modular runtime with Full, Custom and Client-only installation modes.
- A host-local supervisor on every brain host.
- A declared active/standby/degraded/inactive state per module instance.
- Planned migration with checkpoints, health checks, cutover and rollback.
- Recovery after host loss using durable state and explicit leader authority.
- Visual topology showing buildings, departments, agents and migration progress.
- UI/rendering must never block or own runtime execution.

## Core terms

- **Installation ID:** stable identity for an authorized installation; not a display name.
- **Host:** physical/virtual machine running one or more service instances.
- **Module ID:** stable logical department/service identifier.
- **Instance ID:** unique process/service instance on a host.
- **Active leader:** the one instance authorized to coordinate organization-wide tasking.
- **Standby:** compatible, sufficiently synchronized instance allowed to prepare for takeover but not to exercise active-leader authority.
- **Lease/fencing token:** time-bounded authority plus monotonically increasing generation used to reject stale leaders.
- **Checkpoint:** durable, versioned recovery point including state version, event cursor and pending task references.
- **Migration operation ID:** unique idempotency/correlation key for a planned move.
- **Virtual-office event:** observable lifecycle event emitted by the real supervisor or migration coordinator.

## State model

Each module instance should expose a versioned state machine:

`DISCOVERED -> VALIDATING -> INSTALLED -> INACTIVE -> STARTING -> HEALTHY_STANDBY`
or
`... -> ACTIVE`

Operational transitions:
- `ACTIVE -> QUIESCING -> CHECKPOINTING -> TRANSFERRING -> STARTING_AT_DESTINATION -> VERIFYING -> ACTIVE_AT_DESTINATION`
- Source transitions to `STANDBY` only after destination health, state consistency and authority cutover are confirmed.
- Failure states include `DEGRADED`, `UNREACHABLE`, `RECOVERY_REQUIRED` and `QUARANTINED`.
- `INACTIVE` means no module work is running; it does not imply that required recovery packages or persistent data have been deleted.
- Every transition records actor/authority, old/new state, state version, timestamp, reason and operation ID.

Invalid transitions must be rejected by the supervisor. The UI may display requested, acknowledged, running, blocked, failed and completed states, but may not invent transitions.

## Planned migration protocol

1. **Authorize:** owner-authorized command is registered with the active CEO/orchestrator. Check target installation identity, module compatibility, resource capacity, permissions and connectivity.
2. **Plan:** create a durable migration operation with source, target, module set, dependencies, state version, deadline, rollback plan and idempotency key. Show a preview before starting.
3. **Prepare target:** verify signed/approved package, configuration compatibility, secret references, storage capacity and health-check contract. Do not copy raw credentials through the registry or visual events.
4. **Warm standby:** install/start destination in non-authoritative standby mode; transfer allow-listed state and replay durable events to a known cursor.
5. **Quiesce source:** stop accepting new work for the migrating module, or queue it durably. Finish or checkpoint bounded work. Do not silently discard tasks.
6. **Checkpoint and reconcile:** persist a consistent checkpoint; record pending tasks, idempotency keys, source event cursor and schema versions. Exchange-facing state must be reconciled before any retry.
7. **Fence and cut over:** obtain a new valid authority generation/lease, revoke the old generation, and ensure all command receivers reject stale fencing tokens. Never rely on a friendly name or network reachability as authority.
8. **Activate destination:** enable the destination only after it proves the current generation, compatible checkpoint and successful health checks.
9. **Verify:** confirm the destination is processing the expected task/event stream and reporting health. Confirm there is no duplicate owner for side-effecting work.
10. **Demote source:** leave the source in standby if it must provide failover, otherwise mark it inactive. Retain required recovery packages and data.
11. **Commit or rollback:** record final outcome. If destination fails before safe cutover, return authority to the source using a new generation and restore queued work. After cutover, rollback must be another fenced transition, not an unconditional restart.
12. **Visualize:** emit lifecycle events for packing/preparation, departure, transit, arrival, unpacking, health checks and final state. Visual effects may be skipped or accelerated on constrained hardware.

The virtual packing crates, furniture, agents and vehicle are symbolic representations of module/resource migration. They must not imply that physical files or services have moved until the supervisor reports the corresponding completed event.

## High availability and recovery

- Maintain one logical CEO authority at a time. A standby CEO may prepare recovery and observe state, but cannot issue organization-wide commands until it holds the current valid leadership generation.
- Prefer a coordination mechanism that supports leases and fencing. With only two hosts, network partition can make failure detection ambiguous; use a third witness or a coordination service with well-defined consistency where required. Do not claim safe automatic failover based only on missed heartbeats.
- Every authority-sensitive receiver validates the current generation, not just the dashboard or CEO process.
- If leader authority cannot be safely established, fail closed for new organization-wide commands and all execution-adjacent actions. Existing bounded read-only observation may continue.
- Workers may finish previously authorized bounded, non-execution work if policy permits. They must not expand scope or grant themselves new permissions while the CEO is unavailable.
- The standby receives durable events and checkpoints. Define an explicit recovery-point objective (RPO) and recovery-time objective (RTO) per service; do not claim zero data loss unless synchronous durability guarantees it.
- If the standby is stale, incompatible or missing required state, mark it `RECOVERY_REQUIRED`; do not promote it automatically.
- Rejoining former leaders start as non-authoritative standby, reconcile state and acquire a new lease before any future promotion.
- A failed host returning from a partition must be fenced from stale authority before it can resume work.

## State, memory and task durability

Persist and version:
- module and installation manifests;
- organizational topology and permission policy;
- task envelopes, parent/child IDs, idempotency keys and durable queue positions;
- event log/checkpoint cursor and schema versions;
- validated shared-learning artifacts and provenance;
- module health, migration operations and leader generations.

Keep local secrets, exchange API keys, account balances and private financial data outside public discovery metadata and shared-learning artifacts. Replicate only the minimum encrypted/authorized state required for recovery. Namespace storage by owner/organization and installation; verify isolation in tests.

The memory adapter must have a clearly owned lifecycle (open, migrate schema, append/read, flush, checkpoint, close), bounded locking/concurrency behavior, restart recovery, backup/restore and corruption handling. Integration must not accidentally turn memory into a command authority or execution permission.

## Visual office event contract

The runtime emits structured events such as:
- `migration.requested`, `migration.authorized`, `migration.blocked`;
- `module.preparing`, `module.checkpointed`, `module.transfer_started`;
- `module.departed`, `module.arrived`, `module.installing`, `module.health_verified`;
- `leadership.fenced`, `leadership.acquired`, `module.activated`, `module.demoted`;
- `migration.rolled_back`, `migration.completed`, `migration.failed`;
- `standby.sync_progress`, `standby.stale`, `host.unreachable`, `failover.started`, `failover.completed`.

Every event includes event ID, operation ID if applicable, installation ID, host ID, module/instance ID, schema version, state version, timestamp, outcome and a safe reason code. Do not include credentials, secrets, private account details or unrestricted payloads.

The UI maps events to agents, crates, desks, computers and vehicles. If events are missing or stale, the UI must show unknown/degraded state rather than animating success. On low-resource devices, preserve status and controls while reducing or skipping animation.

## Installer and resource policy

- Full: all compatible modules chosen for an all-in-one installation plus the supervisor and common dependencies.
- Custom: selected modules with resolved required dependencies and an explicit installation plan.
- Client-only: cockpit/office client; no local brain services unless separately selected.
- Standby profile: recovery-critical runtime, packages, supervisor, state replication and health checks; suspend expensive workers that are not required for recovery.
- Remove/uninstall a dependency only after checking every module's dependency graph, shared state, backup/rollback plan and standby recovery requirements.
- Module updates are staged and health-checked before activation; preserve last-known-good versions where feasible.
- Office rendering must be a separate client process and must not block the headless brain.

## Acceptance tests

Automated tests should cover:
1. Every legal and illegal state transition.
2. Idempotent duplicate migration requests and event delivery.
3. Destination incompatibility, missing dependency, low disk and failed health check.
4. Source crash before checkpoint, during transfer, during cutover and after cutover.
5. Destination crash before and after acquiring authority.
6. Partition with both hosts alive; stale leader rejected by fencing token.
7. Expired/revoked lease and unavailable coordination service.
8. Stale/corrupt checkpoint, schema migration and replayed event cursor.
9. Duplicate task delivery and safe retry using idempotency keys.
10. Former leader rejoins and remains fenced until reconciled.
11. Standby staleness thresholds and refusal to promote stale state.
12. UI crash, slow rendering and reduced-motion/low-memory modes without stopping runtime.
13. Owner/org data isolation and secret exclusion from events/registry.
14. PAPER/read-only mode invariant across failover; no live orders, transfers, withdrawals or automatic REAL activation.

Physical validation on two actual computers is required for LAN/Tailscale discovery, network partitions, process/host failures, timing, recovery and visual synchronization. CI alone cannot establish this.

## Implementation order

1. Audit existing engine lifecycle, SQLite learning-memory adapter, task persistence, local API authentication and Vercel device/lease routes.
2. Add state-machine and event schemas with validation tests; no behavior changes yet.
3. Integrate memory lifecycle and restart/concurrency/backup tests.
4. Add local supervisor and module manifest/registry.
5. Add durable task/event envelopes and CEO delegation contracts.
6. Implement leader leases/fencing and recovery logic.
7. Implement planned migration/rollback and standby synchronization.
8. Add Vercel peer/installation registry after auditing existing auth and database schema; keep Vercel as control plane, not high-frequency data proxy.
9. Connect the virtual office to real lifecycle events and animate them truthfully.
10. Add installer modes and standby profile.
11. Test on one host, then two physical hosts, then Android-to-PC.
12. Report readiness separately as documented, implemented, automatically tested and physically verified.

## Non-negotiable invariants

- Exactly one valid logical leader generation for authority-sensitive operations.
- The CEO owns organizational tasking and delegation; no worker self-promotes or bypasses task authority.
- Independent Risk Engine and execution guards cannot be overridden by CEO, module, agent, UI or plugin.
- Discovery does not authorize code execution; package integrity and owner policy must be validated.
- UI/rendering is never a runtime dependency.
- Shared learning does not share account authority.
- Development and acceptance tests remain PAPER/read-only.
