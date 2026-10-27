# Extensible Department, Subdepartment and Agent Hierarchy

**Status:** target architecture for staged implementation; not yet implemented end to end.
**Scope:** Vazão Sovereign Trader (VST) only. DGM-MAT remains a separate system.
**Operating safety:** PAPER/read-only for development and integration tests. No live orders, transfers, withdrawals or automatic REAL activation.

## 1. Goal

VST must be able to grow without redesigning the whole application whenever a new department, subdepartment, agent, exchange adapter, strategy family or specialist worker is added. The installer and runtime must consume versioned manifests and registries instead of relying on a fixed list of hard-coded departments.

Examples of future growth:
- Investigation gains subdepartments for exchange documentation, market structure, data quality, news/context and hypothesis validation.
- Analysis gains specialist agents for different symbols, timeframes, regimes or validation methods.
- Trading hosts several exchange/platform teams at once, with platform-specific agents and shared, centrally governed risk controls.
- A department can contain subdepartments, teams and agents several levels deep.
- Any role can run on the same computer as the CEO or on a separate authorized PC/server.

This document records the intended architecture; it is not a claim that dynamic modules or distributed orchestration are already implemented.

## 2. Non-negotiable command hierarchy

**The CEO is the single logical command authority for the VST organization.**

- The CEO owns the organizational tree, task assignment, priorities, delegation boundaries, escalation rules and consolidated reporting.
- A department chief reports to the CEO. A subdepartment chief reports through its parent department. Agents report to their assigned chief.
- New modules do not become autonomous command authorities just because they are installed or discovered.
- Every task that changes organizational work, scope, priority, permissions or accepted conclusions must be registered with the CEO/orchestration authority and traceable to an authorized instruction.
- Agents may exchange bounded working data directly when explicitly permitted, but this does not bypass CEO task ownership, department permissions, central audit or risk controls. The CEO should not have to relay every raw market tick or every byte of internal data; that would create needless latency and a single-process bottleneck.
- If the CEO service is unavailable, workers may finish already-authorized, bounded, non-execution tasks where safe, but must not invent new priorities, expand their authority, approve risk exceptions or authorize trading. Queue new work for reconciliation when the CEO returns.
- The CEO coordinates work; it does not override the independent Risk Engine, data-quality gates, execution guards or explicit owner authorization.

This preserves a central command structure without forcing all high-frequency data through one slow network hop.

## 3. Versioned module registry and manifest

Each installable department, subdepartment, worker and adapter should be declared in a versioned manifest. The runtime registry should support discovery, validation, enable/disable, health, compatibility checks and dependency resolution.

A manifest should include, at minimum:
- stable module ID and manifest/schema version;
- display name, purpose and parent department/module ID;
- module kind: coordinator, department, subdepartment, agent worker, exchange adapter, strategy provider, data provider or client;
- supported protocol/API versions and runtime compatibility;
- required and optional dependencies;
- capabilities requested and permissions required;
- supported deployment modes and resource hints;
- health-check contract and startup/shutdown behavior;
- configuration schema with secret references only, never secret values;
- data ownership, storage namespace and retention/migration requirements;
- upgrade/rollback compatibility and module lifecycle version;
- audit events and output/report schemas;
- explicit declaration of whether the module is observational, analytical, advisory or execution-adjacent.

The registry must reject duplicate stable IDs, incompatible schemas, missing dependencies, unapproved capabilities and invalid parent relationships. Friendly names can change; stable IDs and installation identities must not be derived from display names.

Do not load arbitrary downloaded code merely because it advertises itself to Vercel. Discovery can report a module; installation and activation require a trusted package/signature or other explicit integrity check, compatibility validation and owner-approved policy.

## 4. Hierarchical topology and runtime behavior

The organizational tree is dynamic, but its command rules are stable:

```text
Owner / explicit permissions
          |
     CEO / Orchestrator
          |
   +------+-------------------------+
   |                |               |
Market Research   Analysis        Trading
   |                |               |
   + subdepartments + specialist    + exchange teams
   + agents           agents        + platform agents
                                      |
                             shared Risk Engine / guards
```

- The CEO can delegate a task to a department chief with a task ID, objective, allowed data, deadline, budget/resource ceiling, expected output schema and permitted follow-up actions.
- The chief may break the task into child tasks only within the delegated scope. New scope, conflicting priorities, permission changes, unresolved conflicts or escalation return to the CEO.
- Each child task retains parent-task and originating-command IDs so reports can be traced back through the tree.
- Results should be structured, attributed to module/agent identity, timestamped, evidence-linked and tagged with confidence/validation status.
- The CEO aggregates conflicting reports rather than silently overwriting disagreement. Unresolved conflicts remain explicit.
- A missing, unhealthy, incompatible or disconnected module is reported as unavailable/degraded; it must not be represented as operational.
- The same module ID can run multiple worker instances, but each runtime instance has a unique instance ID, host/install identity and lease. Concurrency must not create duplicate task ownership or duplicate side effects.

## 5. Trading across multiple exchanges and platforms

Trading must support a growing set of platform teams without giving each one an independent authority to move funds or bypass risk controls.

- Each exchange/platform adapter has a stable adapter ID, capability manifest, health status and documented authentication requirements.
- Platform-specific workers may collect public market data, normalize symbols, inspect exchange constraints, measure latency/liquidity and prepare PAPER candidates.
- The CEO assigns cross-platform investigations and coordinates conclusions; platform workers do not redefine organizational priorities on their own.
- A common normalization layer records exchange-specific symbol mapping, precision, minimum order size/notional, fees, rate limits, market status and timestamps. Exchange differences must not be erased by a lossy generic schema.
- Strategy agents produce candidate signals/evidence only. They do not directly submit orders.
- The independent risk and execution pipeline remains authoritative, including data-quality checks, exposure/capital limits, idempotency, client order IDs, execution permissions, reconciliation and audit.
- Exchange credentials remain local to the authorized execution host/secret store. They are not published to Vercel, shared-learning storage, peer discovery or agent messages.
- A new exchange or platform is first added in public-data/read-only mode, then tested in PAPER/replay and out-of-sample validation. Adding a module must never implicitly enable trading permissions or REAL mode.
- One platform's outage, rate limit, malformed data or compromised worker must not disable risk controls or gain authority over other platforms.

## 6. CEO coordination contracts

Use explicit APIs/events rather than informal shared mutable state. The contract should define:
- task request, acceptance, delegation, progress, result, failure, cancellation and escalation;
- priority and deadline handling;
- idempotency key and duplicate-message behavior;
- parent/child task linkage and correlation IDs;
- agent identity, host identity, module version and protocol version;
- evidence references, provenance, confidence and validation state;
- permission/capability checks at both dispatch and service boundary;
- timeout, retry, back-pressure and circuit-breaker behavior;
- durable queue/recovery behavior after process or host restart;
- audit record for command, delegation, policy decision and result.

A worker response is not automatically a verified fact. Evidence collection, independent validation and promotion into shared learning remain distinct stages. Central learning memory is a shared data service, not a command authority and not an execution permission.

## 7. Dynamic installation and updates

The common installer should offer:
1. Full / all-in-one.
2. Custom multi-select, allowing any valid combination of departments, subdepartments and supported worker types.
3. Client-only, for cockpit/chat/office access to an existing brain.

The custom installer resolves dependencies and shows the final plan before changes. The same generic package can install a new module later, subject to compatibility and permission checks. A module may be disabled or removed without reinstalling unrelated departments, but data migration, backups, shared dependencies and rollback must be checked first.

New module lifecycle:
1. Discover metadata from a trusted registry/package source.
2. Validate signature/integrity, manifest schema, compatibility, dependencies and requested permissions.
3. Present any new capability or sensitive permission for explicit owner approval.
4. Install in an isolated module directory/environment where feasible.
5. Register stable module ID and unique runtime instance identity.
6. Run health checks and contract tests in disabled or PAPER mode.
7. CEO acknowledges the module only after health and compatibility pass.
8. Monitor resource use, errors, latency and permission violations.
9. Support disable, rollback and uninstall without corrupting other modules.

Updates must not silently alter the owner, role, permissions, module ID, secrets or execution state. A failed update should return to the last known-good package/configuration where safe.

## 8. Distributed deployment and discovery

- Vercel is the registration/rendezvous/control plane, not the normal department-to-department data path.
- Each authorized installation advertises only necessary metadata: owner/organization, installation ID, hosted module IDs/roles, versions, capabilities, health and short-lived endpoint leases.
- The local supervisor discovers co-located services and prevents duplicate ports, data directories, task ownership and agent identities.
- Private transport prefers a verified, authenticated LAN path when reachable and falls back to authenticated Tailscale. Neither LAN presence nor a friendly agent name is authentication.
- The CEO sees a live logical topology showing which modules and instances are local, remote, healthy, stale or disconnected.
- Commands and delegated work carry authorization and correlation metadata across every host. Service-to-service calls enforce permissions independently of the CEO UI.
- If Vercel is down, already paired nodes may use a bounded valid cache if implemented and tested. New pairing, revoked identities and expired leases fail closed. The local brain should continue safe local observation where policy allows, without public-network exposure or unauthorized execution.
- The virtual office is only a client/visualization layer. A rendering crash or a heavy 3D mode must not block CEO coordination, market collection, risk checks or the headless runtime.

## 9. Split-deployment acceptance test

When a second computer is available, run a controlled test before claiming distributed readiness:

1. Install Full / all-in-one on the primary PC in PAPER/read-only mode.
2. Install Custom on the second PC, initially selecting two departments or worker groups (for example Investigation + Analysis).
3. Register both through Vercel under the same authorized owner/organization.
4. Confirm the CEO topology lists the remote modules with correct host labels, stable IDs, versions and health.
5. Submit a task to the CEO and verify it is delegated to the correct remote chief, then to its agents, and the result returns with parent/child task IDs and evidence.
6. Verify direct worker messages cannot create new authority, change priority outside delegation, bypass CEO task registration or bypass risk controls.
7. Test LAN-first selection and authenticated Tailscale fallback; verify that a transport switch does not replay a non-idempotent command automatically.
8. Stop/restart a worker and the second PC. Confirm leases/health change correctly, queued work recovers safely, duplicate results are rejected and missing departments are reported.
9. Disconnect Vercel and test documented bounded-cache behavior; test revocation and expired leases separately.
10. Verify resource pressure or a virtual-office crash does not stop the headless runtime.
11. Verify all exchange actions remain public-data/read-only or PAPER; no live order, transfer, withdrawal or REAL activation is permitted.
12. Record timings, logs, versions, expected/actual results and unresolved failures in a reproducible test report.

Physical PC-to-PC LAN/Tailscale and Android-to-PC behavior cannot be proven by CI alone.

## 10. Implementation phases

**Phase 1 — Contracts and registry:** define manifest schema, stable IDs, hierarchy rules, capability vocabulary, task envelope and CEO ownership rules. Add schema/contract tests without changing execution behavior.

**Phase 2 — Local hierarchy:** implement a local module registry and supervisor, nested department tree, lifecycle/health checks and duplicate prevention. Exercise several modules on one PC.

**Phase 3 — CEO orchestration:** add durable task/delegation contracts, child-task lineage, timeouts, escalation, structured reports and recovery tests. Ensure workers cannot silently expand scope.

**Phase 4 — Installer integration:** add Full/Custom/Client-only modes, dependency resolution, add/remove module workflow, backup/rollback and module-matrix CI.

**Phase 5 — Multi-host discovery:** audit/reuse the existing authenticated Vercel device/lease design; add the explicit organization/installation/module directory contract; then implement authenticated LAN-first/Tailscale fallback and revocation behavior.

**Phase 6 — Platform teams:** standardize exchange adapter manifests and normalized public-data contracts; test multiple exchange workers concurrently in PAPER/replay; keep execution behind shared independent guards.

**Phase 7 — Physical split test:** install two subsets on two PCs and validate the acceptance test above before reporting distributed deployment as ready.

## 11. Readiness reporting

Report readiness separately for:
- manifest/registry contracts;
- dynamic module lifecycle;
- CEO hierarchy and delegation;
- task durability/recovery;
- multi-exchange worker isolation;
- generic installer and custom selection;
- Vercel registration/discovery;
- LAN/Tailscale private transport;
- resource isolation;
- physical PC-to-PC test;
- Android-to-PC remote control.

A completed document, passing unit tests or a green build does not mean the full feature is implemented. Every status must distinguish **documented**, **implemented**, **automatically tested**, and **physically verified**.

## 12. Safety invariants

- CEO controls organizational tasking, priorities and delegation; no module can promote itself or bypass that hierarchy.
- Risk Engine and execution guards remain independent and cannot be overridden by the CEO, a department, an agent, a plugin or a discovered host.
- No module install/update changes trading mode or grants REAL authority.
- Secrets, credentials, balances and private financial state are not sent through discovery or shared-learning endpoints.
- Shared learning contains only explicitly allow-listed artifacts; knowledge sharing does not share account authority.
- Development and split-deployment tests stay PAPER/read-only.
