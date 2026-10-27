# Internal Priority Failover and Department Placement

**Status:** design contract for staged implementation; no claim of end-to-end automatic failover.
**Scope:** VazaoSovereignTrader only. DGM-MAT remains independent.
**Safety:** development, CI and acceptance tests remain PAPER/read-only. This document does not authorize live trading, transfers, withdrawals or automatic REAL activation.

## Decision

VST should support an **internal-first, priority-ordered recovery policy**. A local host supervisor and the durable state replicated among approved hosts should carry the recovery workflow wherever safe. An external service may remain useful for device discovery, installation enrollment, remote access rendezvous and optional independent coordination, but should not be a hard runtime dependency for ordinary local work or every recovery decision.

Important boundary: a locally stored priority list is a candidate-selection policy, not proof that a former leader is dead. With only two hosts, a network partition can leave both hosts alive but unable to reach each other. A local timer alone cannot safely prove exclusive authority. Internal-only failover is safe only if the system has a real fencing mechanism that all authority-sensitive receivers enforce, or a quorum/independent witness that remains reachable across the relevant failure. If neither is available, fail closed rather than allow split-brain.

## 1. Persistent host priority

Each enrolled organization has a versioned, owner-approved host roster. A record includes:

- stable installation ID and cryptographic identity;
- owner-approved priority rank (1 is preferred);
- eligible roles (CEO standby, selected departments, recovery-only);
- module compatibility and resource capability;
- last confirmed health and durable checkpoint cursor;
- revocation status and protocol/schema versions.

Human labels such as PC1, PC2 and PC3 are display names only. Identity and authorization use installation IDs and keys. Priority changes require an authorized, audited update; a returning or newly enrolled host cannot promote itself by editing local configuration.

Suggested default order:

1. PC1 — preferred CEO host;
2. PC2 — first CEO standby;
3. PC3 — second CEO standby;
4. PC4...PCN — additional eligible standby/department hosts.

The roster survives restart and is replicated to authorized peers. Conflicting or stale roster versions block promotion until reconciled.

## 2. Internal failover state machine

The supervisor should expose observable, versioned states:

`ACTIVE_LEADER -> SUSPECTED_UNAVAILABLE -> WAITING_FOR_SAFE_TAKEOVER -> PROMOTION_PREPARING -> ACTIVE_LEADER`

A candidate may instead enter `STANDBY`, `RECOVERY_REQUIRED`, `FENCED` or `QUARANTINED`. Every transition is durable and has a reason code, operation ID, observed epoch, checkpoint cursor and timestamp.

### Example: PC1 fails

1. PC2 detects missed authenticated heartbeats and enters `SUSPECTED_UNAVAILABLE`. A timeout starts recovery evaluation; it does not immediately grant CEO authority.
2. PC2 waits a configured suspicion/grace interval, then checks whether the current leader's authority is demonstrably expired or revoked and whether stale commands can be fenced at their receivers.
3. PC2 verifies its approved roster rank, key identity, module compatibility, health, durable checkpoint, pending tasks and replication lag against configured recovery-point objectives.
4. If safe, PC2 obtains/activates a strictly newer leadership epoch through the configured fencing/quorum mechanism and verifies the grant. Only then does it become CEO.
5. PC3 remains `HEALTHY_STANDBY`, continues bounded state replication and health checks, and does not independently promote while PC2 holds valid authority.
6. If PC2 is unavailable or cannot safely acquire authority, PC3 evaluates the same conditions against the latest known durable state and authority. Rank alone never overrides a valid higher-priority leader lease.
7. If authority exclusivity cannot be established, the candidate stays standby and the organization enters a degraded/read-only state for authority-sensitive work.

The suspicion timeout, grant/lease duration, renewal interval, acceptable replication lag and recovery deadline must be explicit configuration with safe bounds and clock assumptions. A longer timeout reduces false promotion but increases recovery time. A shorter timeout improves apparent availability but increases false-suspicion risk.

## 3. PC1 returns while PC2 is leader

A returning preferred host must never preempt a healthy active leader merely because its rank is higher.

1. PC1 starts as `FENCED` / non-authoritative `STANDBY`; its saved epoch is stale.
2. PC1 authenticates to peers, loads the current roster and leader epoch, verifies software/schema compatibility, and reconciles its durable event cursor and checkpoint.
3. PC2 remains CEO while PC1 catches up. A stale or corrupt checkpoint sets `RECOVERY_REQUIRED`; it cannot be silently treated as current.
4. Once all required recovery checks pass, the supervisor records `FAILBACK_REQUESTED` according to owner policy (automatic failback may be configured, but must still execute the same guarded protocol).
5. PC2 quiesces organization-wide task assignment at a safe boundary, persists a checkpoint and pending-task/idempotency state, and confirms PC1 is ready.
6. Authority transfers through a new fenced epoch. Receivers reject PC2's previous epoch before PC1 activates CEO services.
7. PC1 becomes leader only after successful activation and health checks. PC2 becomes standby and resynchronizes from PC1.
8. If any precondition fails, abort the cutover, preserve the valid leader, and return the target to standby. After authority has transferred, rollback is another fenced transition with a newer epoch—not an unconditional restart.

If the owner prefers stable failover rather than automatic return, PC2 can remain CEO until the next planned maintenance window. Preferred-host priority is a preference for safe placement, not a preemption command.

## 4. Department placement and contracted host limit

The installation policy may set `max_authorized_hosts` based on the number of contracted/approved installations. Enforce that limit in the enrollment service and in the locally signed/approved roster. A department count must **not** automatically imply one computer per department: several departments may share a host, and one department may have active and standby instances on different hosts if its contract and resources permit.

Each logical department has a placement policy:

- preferred host/rank;
- allowed fallback hosts;
- required dependencies and compatible versions;
- CPU/RAM/storage/network minimums;
- recovery priority (critical, important, deferrable);
- whether a standby copy is required;
- data classification and replication permissions;
- active-instance cardinality (normally one authority-bearing instance for side-effecting roles);
- checkpoint/RPO and recovery/RTO targets.

Default recovery placement order:

1. **Safety and authority controls:** risk guard, fencing verifier, durable task ledger and recovery supervisor. These are prerequisites; if unavailable, do not enable execution-adjacent work.
2. **CEO orchestration:** only after one valid leader authority is established.
3. **Market connectivity and state reconciliation:** restore read-only data collection first; reconcile any pending exchange-facing state before retries.
4. **Central learning memory and task/event journal:** recover consistent, version-compatible state; knowledge sharing never conveys execution authority.
5. **Market Radar, exchange comparison, investigation and analysis:** restore according to resource budgets and task priority.
6. **Fast-response department:** can be restored early for observation/alerting, but remains subordinate to independent risk and execution guards and cannot bypass them.
7. **Virtual office rendering, high-detail animation and other optional presentation services:** last; can be reduced or disabled without affecting the brain.
8. **Optional local AI/research workers:** defer or suspend on resource-constrained hosts; never block the market/risk path.

The exact order is configurable and should be validated against dependencies. A module must not be scheduled on a host that lacks its required dependencies, storage, capacity or permissions. If the preferred host is full, the supervisor should choose the highest-ranked eligible fallback or mark the module `DEFERRED_RESOURCE_LIMIT`, not overload the machine silently.

## 5. Authority and network partition rules

- CEO rank is not authority. A valid current epoch plus receiver-side fencing is authority.
- A heartbeat timeout is suspicion, not proof of power loss.
- A lease that depends only on a host's local clock is insufficient for strict safety under arbitrary clock drift or partitions. Define bounded clock assumptions and receiver behavior, or use a quorum/independent authority mechanism.
- Every side-effecting or authority-sensitive receiver must reject stale epochs, including after restart and network reconnection.
- If the old leader can continue acting while isolated and receivers cannot verify/fence its epoch, automatic promotion must not be enabled.
- If the external coordinator is unavailable, the current leader may continue only within its already-valid grant and configured offline policy. Internal failover may proceed only if the internal fencing/quorum design independently proves exclusivity; otherwise remain degraded/read-only.
- Do not replay non-idempotent commands automatically after network-path changes. Use durable task IDs, idempotency keys and reconciliation.

## 6. Capacity and contract enforcement

The configured host limit must be checked before enrolling a new installation or assigning a new module instance. Re-enrollment of the same cryptographically identified installation should not consume an extra slot, but cloning an installation identity must be rejected. Revocation must invalidate new authority grants and be propagated to receivers before a revoked host can perform authority-sensitive actions.

Contract limits should be explicit and inspectable in the office UI: authorized hosts, enabled modules, standby entitlements, replication budget and optional capabilities. If a limit blocks placement, report the exact reason and the eligible alternatives. Do not silently delete recovery data or remove dependencies to fit a limit.

## 7. Office observability

The virtual office must reflect supervisor events, not simulate success. Recommended events:

- `host.heartbeat_suspected`, `host.unreachable`, `host.rejoined`;
- `leadership.takeover_waiting`, `leadership.takeover_blocked`, `leadership.acquired`, `leadership.fenced`;
- `standby.sync_started`, `standby.sync_progress`, `standby.sync_complete`, `standby.stale`;
- `failback.requested`, `failback.preparing`, `failback.completed`, `failback.aborted`;
- `module.placement_selected`, `module.deferred_resource_limit`, `module.activated`, `module.demoted`.

Every event has an ID, schema version, host/installation ID, module/operation ID where relevant, epoch, state version, timestamp, outcome and safe reason code. Events contain no credentials, private keys, exchange secrets or private financial data. If event delivery is stale, display the last confirmed state and mark it stale/unknown.

## 8. Required acceptance tests

Automated deterministic tests:

1. PC1 timeout alone does not grant PC2 authority.
2. PC2 promotes only after its candidate, checkpoint and fencing/quorum checks pass.
3. PC3 cannot preempt valid PC2 leadership.
4. Old PC1 cannot issue accepted commands after PC2 acquires a newer epoch.
5. PC1 returning starts fenced, reconciles, and does not preempt PC2.
6. Planned failback transfers authority once and aborts safely on each injected failure point.
7. Two hosts isolated by a network partition cannot both retain accepted authority.
8. Coordinator outage follows the documented offline grant policy; no fabricated epoch is created.
9. Stale/corrupt checkpoint blocks automatic promotion.
10. Host limit and placement/dependency/resource constraints are enforced.
11. Duplicate recovery events and task retries are idempotent.
12. Office rendering failure has no effect on leader/supervisor operation.
13. All execution-related tests remain PAPER/read-only and assert no live side effects.

Physical acceptance is still required for power loss, router/LAN partition, Tailscale outage, coordinator outage and PC1 return/failback across at least two real hosts. CI simulations do not substitute for those tests.

## Implementation sequence

1. Audit existing identity, pairing, local tokens, endpoint discovery and supervisor boundaries; do not create duplicate registries.
2. Implement the versioned host roster and pure placement/failover policy with deterministic tests.
3. Implement durable local supervisor state, event journal, checkpoints and recovery cursor.
4. Specify and implement receiver-side fencing/epoch enforcement before enabling automatic takeover.
5. Implement guarded promotion, standby synchronization and planned failback as idempotent state machines.
6. Add placement/resource/contract enforcement and real office event integration.
7. Run CI and PAPER-only fault-injection tests; keep automatic failover disabled until receiver fencing is demonstrated.
8. Perform two-host physical tests and document RPO/RTO, partition behavior and recovery evidence before production activation.


## Deployment boundary: local departments versus remote hosts

This document's PC1/PC2/PC3 recovery model applies **only when VST is explicitly deployed across multiple authorized PCs**. It is not the coordination model for the current installation.

In the current single-PC installation, all departments are local modules coordinated by one CEO/supervisor. They communicate through local runtime interfaces, events/queues and local memory/storage. Do not create or attempt network calls between those modules, and do not invoke distributed leader election, leases, LAN discovery, Tailscale or Vercel to coordinate them. The user handles internal CEO/departement coordination within this one runtime; there is one local CEO, not one CEO per department.

External network access remains a separate concern for configured exchange/API connections, approved services and remote access. Only a future, explicitly enabled multi-PC deployment uses the host roster, inter-PC authenticated communication, external rendezvous/reconciliation and failover rules described here. Keep local module messaging APIs separate from remote-host transport APIs so that adding multiple PCs later does not impose network overhead or distributed failure modes on the single-PC runtime.
