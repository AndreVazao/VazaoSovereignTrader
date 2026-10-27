# External Recovery Coordinator and Leadership Lease Protocol

**Status:** staged architecture and implementation contract. The coordinator and automatic failover are not yet implemented end-to-end.
**Scope:** VazaoSovereignTrader only. DGM-MAT remains separate.
**Development safety:** PAPER/read-only. No live orders, transfers, withdrawals, or automatic REAL activation.

## Purpose

Use an external, durable coordinator to maintain an authoritative view of authorized installations, the current CEO leadership generation, lease expiry, last acknowledged durable state, and recovery progress. Vercel or Render may host the coordinator API, but the decision state must live in a durable transactional database, not process memory or deployment-local files.

The coordinator is a control-plane service. It must not proxy high-frequency market data, normal department messages, exchange credentials, or all runtime traffic. Peer data remains LAN-first and uses the private overlay (such as Tailscale) when LAN is unavailable.

## Roles and records

- **Organization:** security boundary for one private VST installation group.
- **Installation:** stable per-install ID, owner/org membership, public-key identity, approved roles, protocol version, health lease and revocation state.
- **Logical module:** stable department/service ID, independent of the host currently running an instance.
- **Module instance:** installation ID + module ID + unique instance ID.
- **Leadership grant:** organization ID, leader installation ID, monotonically increasing epoch/fencing token, issued-at, expires-at, coordinator revision, and policy/version.
- **State checkpoint:** durable state version, event-log cursor, pending task IDs, schema version, integrity digest, and last confirmed replication time. It excludes credentials and unrelated private financial data.
- **Recovery operation:** durable ID, detected failure evidence, source/target, requested transition, checkpoint chosen, current phase and outcome.

Display names such as “PC 1” and “Joana” are labels, never credentials or authority.

## Coordinator API responsibilities

The coordinator should provide authenticated, owner/org-scoped operations equivalent to:
- register and revoke an installation after proof-of-possession and owner approval;
- publish signed health/heartbeat and module readiness reports;
- read current leader and current epoch;
- request leadership acquisition or renewal;
- atomically grant the next epoch only if policy permits and the prior grant is expired/revoked or explicitly relinquished;
- publish checkpoint metadata and replication cursors;
- record recovery state transitions idempotently;
- expose a read-only topology/status view to the office UI.

Every write must be authenticated, authorized, bounded, replay-resistant where appropriate, and audited. Enforce organization isolation server-side. Never trust client-provided owner IDs without verifying the authenticated identity's membership. Keep installation private keys and exchange credentials on their authorized host. Do not place secrets in discovery metadata, logs, events, or UI payloads.

The database must enforce a single current leadership record per organization and use a transaction/conditional update to increment the epoch. API replicas must not make independent leader decisions from stale local caches. If the database cannot guarantee the required consistency, the coordinator must not issue a new grant.

## Failover protocol: PC 1 unavailable

Example starting state: PC 1 runs CEO + Risk Engine + Research at epoch 42; PC 2 has compatible recovery modules in standby.

1. Both hosts report health, state version, module readiness and replication cursor. PC 2 remains non-authoritative standby.
2. PC 1 heartbeat expires or becomes unreachable. This is suspicion, not proof of physical failure.
3. The coordinator records a suspected failure and checks the current grant, lease expiry, revocation state and organization policy.
4. PC 2 reports its current checkpoint, module compatibility, resource health, and replication lag. If state is too stale or incomplete, it must not promote.
5. Once the previous grant can no longer be valid, PC 2 requests leadership acquisition. The coordinator atomically grants epoch 43 to the approved candidate.
6. PC 2 activates CEO authority only after validating the grant and fencing epoch. Each authority-sensitive receiver must reject commands from expired or older epochs.
7. PC 2 recovers durable tasks/events from the last consistent checkpoint. It reconciles exchange state before any execution-adjacent retry. Development tests remain PAPER/read-only.
8. All peers report their status to the coordinator. The office displays failover progress from actual events, not inferred animations.
9. If the coordinator cannot prove that a single new grant is safe, no new leader is appointed. Read-only observation may continue; new authority-sensitive work fails closed.

The coordinator should record who was the last valid CEO and the last epoch, but **“last CEO” is historical evidence, not sufficient authorization to become CEO again**. Only a valid, current grant and accepted fencing epoch confer authority.

## Why lease plus fencing is required

A timeout alone cannot distinguish a crashed PC from a network partition. An old PC may continue running while disconnected. Therefore:
- leadership grants expire and have a monotonically increasing epoch;
- the old host must stop authority-sensitive work when it cannot renew its lease;
- services receiving authority-sensitive commands validate the current epoch or a securely distributed fencing policy, not just a role name;
- after partition/rejoin, an old host is fenced and must reconcile state as standby;
- no host can self-promote just because it is configured as “CEO standby”.

If an operation cannot validate the current epoch, it must fail closed. Any component that can create side effects must enforce fencing at its own boundary. The dashboard alone is not a security boundary.

## If the external coordinator itself is unavailable

- A current leader may continue only within the safe lifetime and policy of its already-issued grant; it must stop authority-sensitive work when the grant expires.
- Standby nodes cannot invent a new epoch or elect themselves using local timers.
- New leadership cannot be granted until the coordinator/database can make a consistent decision.
- The service may remain in read-only degraded mode where safe.
- The design must define availability vs safety explicitly. Do not silently permit two leaders to improve availability.

For stronger resilience, deploy the API statelessly across replicas while relying on a durable database/consensus mechanism for atomic leadership grants. Hosting multiple API replicas alone does not create a consensus system. Consider an independent witness only if it adds a real failure domain and has well-defined authority; do not count a witness hosted on the same failed machine or in the same failure domain.

## Recovery when PC 1 returns

Do not immediately preempt PC 2 just because PC 1 comes back.

1. PC 1 rejoins with its previous epoch marked stale.
2. It is forced into non-authoritative standby and may not issue CEO commands.
3. It authenticates, downloads the current topology, and reconciles its event cursor/checkpoint with the active leader.
4. It verifies modules, dependencies, memory and durable tasks; stale or corrupt state triggers recovery-required status.
5. PC 2 remains the active leader while health and synchronization are verified.
6. The owner/CEO policy can request a planned failback. That is a new migration/cutover operation with a fresh epoch, checkpoint, quiesce, destination health verification and rollback plan.
7. Only after successful fenced cutover does PC 1 become leader again. Otherwise it remains standby.

If all peers report healthy after recovery, the coordinator should return the organization to its intended steady topology, but not automatically demote a healthy leader without a safe, explicit failback transition.

## Simultaneous failure and stale data

- If both PCs appear offline, preserve the last durable leadership record and checkpoint. A third authorized recovery node can request promotion only after the old grant is no longer valid and the coordinator can safely issue a higher epoch.
- If PC 1 and PC 2 are alive but partitioned, the coordinator can grant only one epoch. The side that cannot renew its grant loses authority. If a peer cannot validate fencing, it must not perform authority-sensitive actions.
- If the coordinator or durable database is partitioned or consistency is uncertain, no conflicting grant may be issued.
- If the candidate checkpoint exceeds the configured maximum replication lag, promotion is blocked or requires an explicit recovery policy and a clearly reported potential loss window.
- Exactly-once processing across crashes cannot be assumed. Use durable task IDs, idempotency keys and reconciliation to avoid duplicate side effects.

## Vercel versus Render

Either platform may host the stateless HTTPS API if its runtime, authentication, timeout, networking and deployment behavior fit the requirements. The choice must be based on verified current platform limits and a testable database design, not brand preference.

Selection criteria:
- durable transactional storage or a separately managed database with required consistency;
- atomic compare-and-swap/transaction for leader epoch;
- secure secret management and key rotation;
- authenticated installation registration and revocation;
- audit logs, monitoring and alerting;
- availability and recovery guarantees that match the chosen lease duration;
- no requirement to keep a server process alive for long-running orchestration;
- no private exchange secrets or high-frequency runtime traffic routed through the coordinator.

Vercel can remain the rendezvous/registry surface if existing routes and authentication support it safely. Render is an alternative host for a coordinator API, not a replacement for durable coordination semantics. Audit the existing Vercel routes, Supabase schema, device proof-of-possession and endpoint lease implementation before adding new tables or reusing existing IDs. Cloud device IDs, local pairing IDs and installation IDs must remain distinct unless a reviewed mapping explicitly relates them.

## Required observability

Expose safe status fields to the office:
- current leader installation, module roles and epoch;
- grant expiry and last successful renewal;
- standby readiness and replication lag;
- latest consistent checkpoint and event cursor;
- suspected failure versus confirmed lease expiry;
- recovery phase, blocked reason, and last transition;
- returning host reconciliation and failback status.

Do not expose private IPs unnecessarily, keys, bearer tokens, exchange credentials, balances, orders, or unrestricted private state.

## Acceptance tests

1. Atomic concurrent requests cannot grant the same epoch to two installations.
2. A lease expiry is required before ordinary failover; historical last-leader record alone never promotes a host.
3. Stale epochs are rejected by every authority-sensitive receiver.
4. Old leader continues after partition but cannot renew: it is fenced after grant expiry.
5. Coordinator API restart/scale-out does not reset epoch or duplicate leader grants.
6. Database unavailable or uncertain: no new leadership grant.
7. PC 2 is stale, incompatible, unhealthy or revoked: promotion is denied.
8. PC 1 returns with old epoch: remains standby until reconciled.
9. Planned failback requires a new epoch and migration verification.
10. Simultaneous loss of PC 1 and PC 2 does not invent a leader; authorized third node may recover only through the same lease/fencing protocol.
11. Duplicate/replayed heartbeat, migration request and task events are idempotent or rejected.
12. Owner/org isolation, proof-of-possession, revocation, replay protection and audit records are verified.
13. PAPER/read-only invariant survives leadership changes.
14. Physical tests cover LAN loss, Tailscale fallback, coordinator outage, machine power loss and network partition.

## Implementation plan

1. Inspect current Vercel API routes, Supabase migrations, private device registration, proof-of-possession and endpoint lease flow.
2. Document exact identity mappings and existing authorization boundaries; do not create a parallel registry prematurely.
3. Add typed lease/grant/checkpoint schemas and pure policy tests.
4. Implement a durable transactional leader-epoch store and authenticated coordinator API.
5. Integrate lease renewal and fencing checks into local supervisor and every authority-sensitive receiver.
6. Add replicated checkpoint/event cursor and standby readiness reports.
7. Integrate failover/failback orchestration with migration lifecycle.
8. Connect virtual office to coordinator and supervisor events.
9. Run chaos tests in CI, then validate on two physical hosts and a real coordinator/database.
10. Report readiness separately as documented, implemented, automatically tested and physically verified.
