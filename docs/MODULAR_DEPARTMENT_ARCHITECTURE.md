# Modular Department Architecture and Shared Internal Learning Memory

Status: architecture contract / planned design. This document does not claim that all departments or execution paths are implemented.

## Purpose

Sovereign Trader is designed as a modular trading organisation. It starts on one PC, with several logical departments sharing one authoritative internal learning memory. Later, individual departments may move to separate machines without changing domain contracts or creating duplicate trading authority.

This is internal, same-system memory. It is distinct from any future cross-installation or cross-computer learning exchange, discovery service, Vercel coordination, or user-to-user knowledge sharing. Those systems must have separate interfaces, permissions, and lifecycle policies.

## Initial logical departments

- **CEO / Orchestrator:** coordinates tasks, prioritises work, tracks evidence and uncertainty, and enforces configured operating policy. The human owner remains the authority for policy and any required approvals.
- **Research:** discovers venues, market mechanisms, data sources, and candidate hypotheses.
- **Market Analysis:** evaluates signal quality, timing, data integrity, reproducibility, and statistical evidence.
- **Exchange Comparison:** compares normalized instruments and executable bid/ask, depth, fees, latency, availability, and venue-specific constraints.
- **Risk and Validation:** independently checks expected net economics, uncertainty, exposure, stale data, operational failure modes, and policy limits.
- **Rapid-Bet Department:** a specialised, latency-sensitive consumer of already validated opportunities. It remains dormant unless explicitly enabled by policy. It cannot bypass risk gates, human approval requirements, or server-side execution authorization.
- **Market-data / telemetry services:** maintain feed health, event provenance, clock/receive timing, and freshness signals consumed by the other departments.

These are logical boundaries first, not a requirement to run one operating-system process per department. On a single PC they can initially be modules or supervised workers. Separate processes and separate computers are later deployment options.

## Shared internal learning memory

All departments read from one authoritative, local memory service/API. The memory should support:

- versioned facts and hypotheses with provenance, source timestamps, local receive timestamps, and collection/processing timestamps;
- explicit confidence, validation status (unverified, testing, supported, rejected, stale), scope, and expiry/freshness;
- experiment definitions, reproducible results, negative results, costs, uncertainty, and known failure modes;
- append-only evidence/audit history for material status changes;
- fast indexed reads and event-based invalidation/notification so departments do not repeatedly recompute the same work;
- idempotent writes, conflict/version handling, bounded caches, and clear behaviour when the memory service is unavailable;
- separate namespaces and access policies for internal learning versus future cross-installation knowledge exchange.

The shared memory is not a magical instantaneous source of truth. Freshness metadata and read-after-write/version guarantees must be explicit. A cache may accelerate reads but cannot silently present stale evidence as current. High-frequency market data should use a dedicated low-latency event/data path; durable learning memory stores derived knowledge, evidence and references rather than becoming a slow database queried for every tick.

## Candidate opportunity lifecycle

1. Research records a candidate hypothesis with provenance and uncertainty.
2. Market-data and exchange-comparison services normalize observations and assess feed health, timestamps, executable bid/ask and depth.
3. Analysis replays the evidence without look-ahead, testing clock uncertainty, collector/network delay, fees, spread, slippage, fill probability, adverse selection and latency percentiles.
4. Risk and Validation either rejects the candidate, requests more evidence, or publishes a time-bounded validated opportunity with explicit conditions and limits.
5. The Rapid-Bet Department can react only while that validation is still fresh and all execution prerequisites remain satisfied. If quote, depth, latency budget, risk limits, or authorization is no longer valid, the opportunity expires and no trade is attempted.
6. Any future execution path must be a single authoritative, server-side order authority with idempotent intents, reconciliation of unknown outcomes, audit logs, explicit policy gates, and human approval wherever configured. No department may create a competing order engine.

A detected difference between displayed prices or exchange timestamps is not enough. The system must demonstrate that a net positive, executable edge survives measurement uncertainty, realistic arrival latency, costs and operational risk. Until then the workflow remains read-only, replay, or PAPER shadow mode with no exchange orders.

## Latency and coordination principles

- Use local monotonic receive time for ordering observations captured by the same instrumented collector; retain exchange event timestamps as separate fields.
- Publish compact, versioned events for important state changes rather than polling the entire memory continuously.
- Keep hot market data and durable learning/evidence storage as separate layers with explicit interfaces.
- Give each department a declared responsibility, input/output schema, freshness budget, health state and failure policy.
- Prefer bounded queues, backpressure, deduplication, and observable queue age to unbounded work accumulation.
- If data is stale, clocks are uncertain, the memory is unavailable, or a required department is unhealthy, fail closed for rapid execution and surface the reason to the CEO/operator.
- Measure end-to-end delay by stage; do not infer speed from UI responsiveness or worker count alone.

## Growth from one PC to a distributed organisation

1. **Single-PC phase:** one backend, one local memory service, logical departments supervised within the same deployment.
2. **Process-isolated phase:** resource-intensive departments can run as separate local processes while keeping the same contracts.
3. **Multi-computer phase:** move research, analysis or market-data workers to dedicated machines. The central backend/order authority and shared memory remain authoritative; workers send versioned results/events and never maintain competing execution state.
4. **Visual office phase:** the office is an observation/control surface that reflects real department health, assignments, evidence and state. Characters and rooms are presentation only, adapt to device capability, and must never fabricate activity. New agents can be represented visually only after the underlying worker exists and reports real status.

The visual building can grow as actual capacity grows. It must not be necessary to render the office for the trading system to function; chat-only and compact modes remain valid.

## Non-goals and safety boundaries

- No exchange API keys or trading authority in PC/mobile visual clients.
- No unauthenticated LAN/Tailscale shortcuts and no public port exposure.
- No direct live orders, transfers or withdrawals from research/analysis agents.
- No automatic promotion of an unverified hypothesis to executable status.
- No mixing of internal learning memory with future external/shared learning between installations.
- No claim of zero latency: the design minimises, measures and bounds delay rather than pretending it can be eliminated.

## Initial acceptance criteria

- Two or more logical departments can read the same versioned learning record and see the same validation state.
- A write or invalidation makes freshness/version changes observable without requiring a full-memory scan.
- Stale, missing, conflicting or unverified evidence cannot activate the Rapid-Bet Department.
- A simulated opportunity expires when its freshness budget or latency budget is exceeded.
- No test or prototype sends a real exchange order.
- Department health and the reason for any blocked opportunity are visible to the CEO/operator.
- The same department contracts can be exercised locally and, in later work, across a process boundary without changing the single authoritative order path.
