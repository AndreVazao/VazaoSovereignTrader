# Reception and Distributed Virtual Office Contract

## Purpose

The Virtual Office should behave like a real company while preserving three valid conversation paths: the CEO chat is the default for general requests and coordination; the owner may open a direct conversation with any department; and Reception is an optional routing path for requests the owner wants classified or delegated. The selected conversation owns its task/history correlation, and results return to that originating conversation.

The Runtime/brain is authoritative. CEO coordination, Reception, department chats, dashboard, office rendering and avatars are clients/orchestration surfaces—not a second engine and not an alternate trading authority.

## Topology: local first, distributed by design

The first deployment may run Runtime, dashboard and Virtual Office on the same PC. Interfaces must not depend on that arrangement:

- Runtime is a separately addressable service with its own lifecycle and source of truth.
- Dashboard and Virtual Office connect through versioned, authenticated contracts; they must not instantiate a second Runtime.
- Co-located communication may use a local transport. Remote communication must use authenticated transport over a private network (Tailscale is the preferred private connectivity path in the current deployment plan).
- Discovery/rendezvous is not an authentication boundary. A successful discovery response must never by itself authorize commands.
- Credentials must not be placed in URLs, logs, browser persistent storage or rendered snapshots. Enforce authorization on the Runtime/API for every private endpoint.
- The office can be closed, disconnected, moved to another host or fail to render without stopping the Runtime.

## Conversation paths and Reception responsibilities

### CEO chat — default path

The CEO / Runtime coordinator is the owner's primary conversation and default landing chat. It handles general questions, system status, priorities and delegation. It may answer directly or coordinate departments and consolidate their results. The CEO coordinator is part of the authoritative Runtime, not merely a visual avatar.

### Direct department chat

The owner may click any department and speak to it directly, without a mandatory Reception or CEO hop. Each department chat keeps its own conversation identity and task history, within its explicit permission/capability scope. Direct access is a communication choice, not an authorization escalation; all execution and risk decisions remain under the authoritative Runtime and server-side guards.

### Reception — optional routing path

Reception is available when the owner wants help classifying a request or does not know which department is appropriate. It is not a mandatory entry point for CEO or direct department conversations.

When selected, Reception:

1. **Captures** the original request and conversation/task correlation ID.
2. **Classifies** intent (status/diagnostics, research, analysis, exchange comparison, learning review, operational control, or a request needing human decision).
3. **Clarifies** with one focused question when materially ambiguous or missing an essential parameter. Do not silently invent symbol, venue, time window, risk budget or execution intent.
4. **Authorizes** by resolving the authenticated user's identity and allowed scopes before dispatch. Natural language is not a substitute for server-side authorization.
5. **Routes** a typed task to the responsible department using a stable task contract. Reception must not directly execute exchange operations.
6. **Tracks** queued/running/waiting-for-owner/completed/failed/cancelled/unknown status, timestamps, responsible department and bounded progress updates.
7. **Returns** the outcome, evidence/freshness, uncertainties and any next decision needed in the same Reception thread.

If a remote request times out after a mutation could have started, show outcome as unknown and reconcile before any retry. Never blindly replay an action.

## Department boundaries

Initial logical departments:

- **Research:** gather public/authorized observations and research hypotheses; no execution authority.
- **Analysis:** assess data quality, freshness, uncertainty, costs and evidence; label hypotheses versus validated findings.
- **Exchange comparison:** align observations by venue/symbol/event-time semantics and compare exchange-specific capabilities. It must not label polling order as executable lead/lag without validated evidence.
- **Learning and memory:** persist/retrieve provenance-bearing lessons with freshness, versioning and owner scope. Local shared Runtime learning memory is distinct from any future cross-device knowledge-sharing layer.
- **Fast reaction / execution:** evaluate time-sensitive candidates and, only if separately authorized, submit through the existing engine risk and execution gates. It cannot bypass risk checks, create REAL authorization, or treat conversational wording as order authorization.
- **CEO / Runtime coordinator:** owns task scheduling and system-level decisions, applies policy, and consolidates department output. This is part of the authoritative Runtime, not a visual avatar.

Department labels may be shown as office rooms/characters, but visual state is only a representation of authoritative task state. A character animation must never be the source of task status.

## Task contract and event handling

Every routed task should have:

- opaque task ID and conversation/correlation ID;
- authenticated owner/tenant scope;
- typed intent and validated parameters;
- requesting department and assigned department;
- creation/update timestamps and freshness deadline where applicable;
- explicit permission/capability requirements;
- state and bounded progress summary;
- evidence/provenance references and uncertainty classification;
- cancellation semantics and an idempotency key for any supported mutation.

Progress notifications are observational. Use bounded latest-value snapshots or coalesced events for the office; slow consumers may miss intermediate visual updates. Durable audit/risk events must use their own persistence path, never the lossy visual queue.

## Runtime non-blocking requirement

- Runtime starts and operates without dashboard or office.
- Conversation panels and department UIs never hold engine, risk, market-data or order locks across network I/O, rendering, serialization or acknowledgement.
- Office refresh uses lightweight snapshots; no full diagnostic aggregation on every refresh.
- Observer queues are bounded. Superseded visual updates may be coalesced/dropped.
- Under measured latency/resource pressure, reduce office update frequency and rendering fidelity, then disable visual rendering if necessary. Do not alter Runtime risk policy or engine scheduling to preserve animation.
- A chat/dispatch failure must not stop research, market-data collection, risk processing or engine cycles.
- Keep manual/operator-visible control separate from display-only actions.

## Acceptance tests before implementation is considered complete

1. Same-PC and separate-host clients connect to the same Runtime without creating a second engine.
2. Unauthenticated and under-scoped requests are rejected at the API boundary.
3. Ambiguous requests cause a clarification rather than guessed execution parameters.
4. Research, analysis and exchange-comparison requests route to the expected department; unsupported intents fail visibly and safely.
5. Task status and final response remain correlated to the originating CEO, department or Reception thread.
6. Direct department conversations do not pass through Reception unless explicitly requested.
7. Disconnect/reconnect, server restart, expired credentials, malformed responses and slow clients do not corrupt task state.
8. Observer saturation/coalescing does not create unbounded memory growth or block Runtime cycles.
9. Visual degradation/disablement leaves Runtime lifecycle and risk policy unchanged.
10. Any execution-capable request still passes the existing engine risk/execution gates and explicit authorization checks.
11. Logs and snapshots do not contain access tokens, exchange secrets or other credentials.

## Implementation sequence

1. Keep the current authenticated office read-only while establishing conversation and task contracts.
2. Implement deterministic routing and task-state tracking before adding general LLM interpretation.
3. Add department adapters behind typed interfaces and existing permission scopes.
4. Add remote transport/discovery only after local contracts and authentication are tested.
5. Add visual department/character behavior as an optional projection of task events.
6. Measure Runtime cycle latency with office absent, normal and saturated; implement a threshold-based visual circuit breaker from measured baselines.

## Current status

This document specifies the target contract. It does not claim that a complete Reception dispatcher, direct department chats, distributed transport, automatic visual circuit breaker, or end-to-end multi-host validation already exists. The cached observer endpoint reduces HTTP-path work, but publication still briefly acquires the engine lock after cycles/transitions; performance and saturation evidence remain outstanding.
